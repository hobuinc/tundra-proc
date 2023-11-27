
## This is the script that produces the pipelines and executes them with
## Bash on a docker container
import os
import sys
from s3pathlib import S3Path
import shlex
import subprocess
import pdal
import tempfile
import pathlib
import gzip
import shutil

#uri = 's3://grid-dev-lidarscans/Fairbanks-A-TLS/rxp/'




def run(command):
    args = shlex.split(command)
    p = subprocess.Popen(args,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    ret = p.communicate()

    if p.returncode != 0:
        error = ret[1].decode('utf-8', 'replace')
        raise RuntimeError(error)

    response = ret[0].decode('utf-8', 'replace')
    return ret


# s3://grid-dev-lidarscans/Fairbanks-A-TLS/rxp/20220520-0304-09.MAIN.frame.rxp.gz


def make_tempfile(fname, suffix='.rxp.gz'):
    tmp = next(tempfile._get_candidate_names())
    tmpdir = tempfile.gettempdir()
    path = os.path.join(tmpdir, tmp, 'tempfile')
    p = pathlib.Path(path)
    p.mkdir(parents=True, exist_ok=True)
    path = (p / fname).with_suffix(suffix)
    p = pathlib.Path(path)
    return p

def make_tempdir():
    p = pathlib.Path(os.environ['TMPDIR'])
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)

    return p

def fetch(s3path):
    gzfilename = make_tempfile(s3path.fname)

    # s3pathlib automatically unpacks gz files
    with s3path.open(mode='rb') as gzfile:
        with gzfilename.open(mode='wb'):
            gzfilename.write_bytes(gzfile.read())

    rxpfilename = gzfilename.rename((gzfilename.parent / gzfilename.name).with_suffix('.rxp'))
    options['rxp_filename'] = rxpfilename

    return rxpfilename


def rxp_pipeline(rxpfilename):
    reader = pdal.Reader.rxp(str(rxpfilename),
                             sync_to_pps=True,
                             reflectance_as_intensity=True,
                             spatialreference="EPSG:7789")

    pop_matrix = '2022-HDZ-ATLS-POP.dat'
    sop_matrix = '20220701-0304-08-SOP.dat'
    sop = pdal.Filter.transformation(matrix=sop_matrix)
    pop = pdal.Filter.transformation(matrix=pop_matrix)
    reprojection = pdal.Filter.reprojection(out_srs="EPSG:32606")

    ferry = reader | sop | pop | reprojection | pdal.Filter.ferry(dimensions = "Intensity => PointSourceId")

    stage = ferry

    if 'MAIN' in options['basename']:
        overlay = ferry | pdal.Filter.overlay(datasource="crop.vrt",
                                      layer="CROP",
                                      dimension="PointSourceId",
                                      column="tessellate")
        expression = overlay | pdal.Filter.expression(expression="PointSourceId == 1")
        stage = expression

        stage = stage | pdal.Filter.elm() | pdal.Filter.outlier() | pdal.Filter.smrf(where="Classification != 7" )

    las_filename = options['las_filename']
    print(las_filename)
    las_writer = stage | pdal.Writer.las(str(las_filename),
                                    a_srs="EPSG:32606",
                                    scale_x=0.001,
                                    scale_z=0.001,
                                    scale_y=0.001,
                                    minor_version="4",
                                    offset_x="auto",
                                    offset_y="auto",
                                    offset_z="auto",
                                    extra_dims="Roll=float, Pitch=float, EchoRange=float, Amplitude=float, Reflectance=float, Deviation=float, BackgroundRadiation=float"
                                    )
    if 'MAIN' in options['basename']:
        dtm_filename = options['dtm_filename']
        dsm_filename = options['dsm_filename']
        dtm_writer = las_writer | pdal.Writer.gdal(str(dtm_filename),
                                                resolution=0.25,
                                                output_type="idw",
                                                data_type="float32",
                                                where="Classification == 2",
                                                gdalopts="COMPRESS=LERC, TILED=YES, MAX_Z_ERROR=0.001"
                                    )
        dsm_writer = dtm_writer | pdal.Writer.gdal(str(dsm_filename),
                                                resolution=0.25,
                                                output_type="idw",
                                                data_type="float32",
                                                where="Classification != 7",
                                                gdalopts="COMPRESS=LERC, TILED=YES, MAX_Z_ERROR=0.001"
                                    )
    else:
        dtm_writer = las_writer


    return dsm_writer


def pivox_pipeline(filename):
    reader = pdal.Reader.las(str(filename),
                             spatialreference="EPSG:7789")

    pop_matrix = '2022-HDZ-ATLS-POP.dat'

    sop_matrix = None
    if 'PIVOX1' in filename.name:
        sop_matrix = '2022-HDZ-PIVOX1-SOP.dat'
    if 'PIVOX2' in filename.name:
        sop_matrix = '2022-HDZ-PIVOX2-SOP.dat'
    if 'PIVOX3' in filename.name:
        sop_matrix = '2022-HDZ-PIVOX3-SOP.dat'
    sop = pdal.Filter.transformation(matrix=sop_matrix)
    pop = pdal.Filter.transformation(matrix=pop_matrix)
    reprojection = pdal.Filter.reprojection(out_srs="EPSG:32606")
    ferry = reader | sop | pop | reprojection

    assign = ferry | pdal.Filter.assign(value =
      "ReturnNumber = 1 WHERE ReturnNumber < 1")

    assign2 = assign | pdal.Filter.assign(value =
      "NumberOfReturns = 1 WHERE NumberOfReturns < 1")

    stage = assign2 |  pdal.Filter.smrf(where="Classification != 7")
    overlay = stage | pdal.Filter.overlay(datasource="crop.vrt",
                                      layer="CROP",
                                      dimension="PointSourceId",
                                      column="tessellate")
    expression = overlay | pdal.Filter.expression(expression="PointSourceId == 1")

    las_filename = options['las_filename']
    print(las_filename)
    las_writer = stage | pdal.Writer.las(str(las_filename),
                                    a_srs="EPSG:32606",
                                    scale_x=0.001,
                                    scale_z=0.001,
                                    scale_y=0.001,
                                    minor_version="4",
                                    offset_x="auto",
                                    offset_y="auto",
                                    offset_z="auto"
                                    )
    dtm_filename = options['dtm_filename']
    dsm_filename = options['dsm_filename']
    dtm_writer = las_writer | pdal.Writer.gdal(str(dtm_filename),
                                            resolution=0.25,
                                            output_type="idw",
                                            data_type="float32",
                                            where="Classification == 2",
                                            gdalopts="COMPRESS=LERC, TILED=YES, MAX_Z_ERROR=0.001")

    dsm_writer = dtm_writer | pdal.Writer.gdal(str(dsm_filename),
                                            resolution=0.25,
                                            output_type="idw",
                                            data_type="float32",
                                            where="Classification != 7",
                                            gdalopts="COMPRESS=LERC, TILED=YES, MAX_Z_ERROR=0.001")

    return dsm_writer


def cleanup(tmpdir):

    if tmpdir.exists():
        shutil.rmtree(str(tmpdir))





def upload():
    bucket = options['uri'].bucket

    dtm = "atls-dtm-cropped"
    laz = "atls-laz-classified"
    pivox_pc = "pivox-laz-classified"
    pivox_raster = "pivox-dtm"


    def push(filename, output_dir):
        print(f'uploading local file {filename}')
        path = S3Path.from_s3_uri(f"s3://{bucket}/Fairbanks-A-TLS/{output_dir}/{filename.name}")
        print(f'Pushing to {path}')

        print(f'does local file exist? {filename.exists()}')
        with filename.open(mode='rb') as f:
            path.write_bytes(f.read())

    if 'PIVOX' in str(options['copc_filename']):
#         push(options['copc_filename'], 'pivox-laz-classified')
#         if options['dtm_filename'].exists():
#             push(options['dtm_filename'], 'pivox-dtm')
        if options['dsm_filename'].exists():
            push(options['dsm_filename'], 'pivox-dsm')

    else:
#         push(options['copc_filename'], 'atls-laz-classified')
        if options['dsm_filename'].exists():
            push(options['dsm_filename'], 'atls-dsm-cropped')
#         if options['dtm_filename'].exists():
#             push(options['dtm_filename'], 'atls-dtm-cropped')


def run_copc_pipeline():

    dims = ['Intensity','ReturnNumber','NumberOfReturns','Classification','ScanAngleRank']
    dims = dims + ['GpsTime','Amplitude','Reflectance','Pitch','Roll','Deviation','BackgroundRadiation']
    dims = dims + ['EchoRange']
    dims = ','.join(dims)
    command = f"untwine -i {str(options['las_filename'])} -o {str(options['copc_filename'])} --single_file --dims \"{dims}\""
    run(command)

def run_pipeline(pipeline):
    print (pipeline.pipeline)
    with options['pipeline_filename'].open(mode='w') as f:
        f.write(pipeline.pipeline)

    command = f"pdal pipeline -i {str(options['pipeline_filename'])} --debug --verbose 6"
    stdout, stderr = run(command)

if __name__ == '__main__':

    uri = sys.argv[1]
    upload_path = sys.argv[2]
    print(uri)

    doCleanup = True
    if len(sys.argv) > 3:
        doCleanup = False

    tmpdir = make_tempdir()
    s3path = S3Path.from_s3_uri(uri)

    options = {}
    options['uri'] = s3path
    options['pipelines'] = []
    options['basename'] = s3path.fname

    copc_filename = make_tempfile(options['basename'], '.copc.laz')
    las_filename = make_tempfile(options['basename'], '.las')
    dtm_filename = make_tempfile(options['basename'], '.tif')
    dsm_filename = make_tempfile(options['basename'], '.tif')
    pipeline_filename = make_tempfile(options['basename'], '.json')
    options['copc_filename'] = copc_filename
    options['las_filename'] = las_filename
    options['dtm_filename'] = dtm_filename
    options['dsm_filename'] = dsm_filename
    options['pipeline_filename'] = pipeline_filename

    try:
        filename = fetch(s3path)

        if 'rxp' in s3path.fname:
            pipeline = rxp_pipeline(filename)
            run_pipeline(pipeline)

            run_copc_pipeline()

        if 'PIVOX' in s3path.fname:
            pipeline = pivox_pipeline(filename)
            run_pipeline(pipeline)
            run_copc_pipeline()

        upload()
        cleanup(tmpdir)

    finally:
        cleanup(tmpdir)


