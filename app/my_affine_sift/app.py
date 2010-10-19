"""
ASIFT demo interaction script
"""
# pylint: disable-msg=C0103

from lib import base_app
from lib import get_check_key, http_redirect_303, app_expose
from lib import image
from cherrypy import TimeoutError
import cherrypy
import os.path
import time

class app(base_app):
    """ demo app """
    
    title = "ASIFT: A New Framework for Fully Affine Invariant Comparison"
    description = """This program performs the affine scale-invariant
    matching method known as ASIFT.<br />
    Please select two images; color images will be converted into gray
    level."""

    input_nb = 2
    input_max_pixels = None
    input_max_method = 'zoom'
    input_dtype = '1x8i'
    input_ext = '.png'
    timeout = 60
    is_test = False

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # index() is generic
        app_expose(base_app.index)
        app_expose(base_app.input_select)
        app_expose(base_app.input_upload)
        # params() is modified from the template
        app_expose(base_app.params)
        # run() and result() must be defined here

    # run() is defined here,
    # because the parameters validation depends on the algorithm
    @cherrypy.expose
    @get_check_key
    def run(self):
        """
        params handling and run redirection
        """
        # no parameters
        http_redirect_303(self.url('result', {'key':self.key}))
        urld = {'input' : [self.url('tmp', 'input_0.png'),
                           self.url('tmp', 'input_1.png')]}
        return self.tmpl_out("run.html", urld=urld)

    # run_algo() is defined here,
    # because it is the actual algorithm execution, hence specific
    # run_algo() is called from result(),
    # with the parameters validated in run()
    def run_algo(self, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        asift = self.run_proc(['asift', 'input_0.png', 'input_1.png', 
                               'outputV.png', 'outputH.png',
                               'match.txt', 'keys_0.txt', 'keys_1.txt'],
                              stdout=stdout, stderr=stdout)
        sift = self.run_proc(['sift', 'input_0.png', 'input_1.png', 
                              'outputV_SIFT.png', 'outputH_SIFT.png',
                              'match_SIFT.txt',
                              'keys_0_SIFT.txt', 'keys_1_SIFT.txt'],
                             stdout=None, stderr=None)
        self.wait_proc([asift, sift], timeout)
        return

    @cherrypy.expose
    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # no parameters
        stdout = open(self.path('tmp', 'stdout.txt'), 'w')
        try:
            run_time = time.time()
            self.run_algo(timeout=self.timeout, stdout=stdout)
            run_time = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout',
                              errmsg="""
The algorithm took more than %i seconds and had to be interrupted.
Try again with simpler images.""" % self.timeout)
        except RuntimeError:
            return self.error(errcode='retime',
                              errmsg="""
The program ended with a failure return code,
something must have gone wrong""")
        self.log("input processed")

        match = open(self.path('tmp', 'match.txt'))
        nbmatch = int(match.readline().split()[0])
        match_SIFT = open(self.path('tmp', 'match_SIFT.txt'))
        nbmatch_SIFT = int(match_SIFT.readline().split()[0])

        urld = {'new_run' : self.url('params'),
                'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_0.png'),
                           self.url('tmp', 'input_1.png')],
                'output_h' : self.url('tmp', 'outputH.png'),
                'output_v' : self.url('tmp', 'outputV.png'),
                'output_v_sift' : self.url('tmp', 'outputV_SIFT.png'),
                'match' : self.url('tmp', 'match.txt'),
                'keys_0' : self.url('tmp', 'keys_0.txt'),
                'keys_1' : self.url('tmp', 'keys_1.txt')}
        stdout = open(self.path('tmp', 'stdout.txt'), 'r')
        img_out = image(self.path('tmp', 'outputV.png'))
        return self.tmpl_out("result.html", urld=urld,
                             run_time="%0.2f" % run_time,
                             nbmatch=nbmatch,
                             nbmatch_SIFT=nbmatch_SIFT,
                             height=str(img_out.size[1]+10),
                             stdout=stdout.read())
