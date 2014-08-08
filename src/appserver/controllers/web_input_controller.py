import logging
import os
import sys
import json
import cherrypy

from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
import splunk.appserver.mrsparkle.controllers as controllers

import splunk.util as util
import splunk.entity as entity

sys.path.append( os.path.join("..", "..", "..", "bin") )
sys.path.append(make_splunkhome_path(["etc", "apps", "website_input", "bin"]))

from web_input import URLField, DurationField, SelectorField, WebInput
from modular_input import Field, FieldValidationException

def setup_logger(level):
    """
    Setup a logger for the REST handler.
    """

    logger = logging.getLogger('splunk.appserver.lookup_editor.controllers.LookupEditor')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'web_input_controller.log']), maxBytes=25000000, backupCount=5)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger(logging.INFO)

class WebInputController(controllers.BaseController):
    '''
    Controller for previewing output of a web-input
    '''
 
    def render_error_json(self, msg):
        """
        Render an error such that it can be returned to the client as JSON.
        
        Arguments:
        msg -- A message describing the problem (a string)
        """
        
        output = jsonresponse.JsonResponse()
        output.data = []
        output.success = False
        output.addError(msg)
        return self.render_json(output)
 
    @staticmethod
    def getCapabilities4User(user=None, session_key=None):
        """
        Get the capabilities for the given user.
        """
        
        roles = []
        capabilities = []
        
        # Get user info              
        if user is not None:
            logger.info('Retrieving role(s) for current user: %s' % (user))
            userDict = entity.getEntities('authentication/users/%s' % (user), count=-1, sessionKey=session_key)
        
            for stanza, settings in userDict.items():
                if stanza == user:
                    for key, val in settings.items():
                        if key == 'roles':
                            logger.info('Successfully retrieved role(s) for user: %s' % (user))
                            roles = val
             
        # Get capabilities
        for role in roles:
            logger.info('Retrieving capabilities for current user: %s' % (user))
            roleDict = entity.getEntities('authorization/roles/%s' % (role), count=-1, sessionKey=session_key)
            
            for stanza, settings in roleDict.items():
                if stanza == role:
                    for key, val in settings.items():
                        if key == 'capabilities' or key =='imported_capabilities':
                            logger.info('Successfully retrieved %s for user: %s' % (key, user))
                            capabilities.extend(val)
            
        return capabilities     
    
    @expose_page(must_login=True, methods=['GET', 'POST']) 
    def scrape_page(self, url, selector, **kwargs):
        """
        Perform a page scrape and return the results (useful for previewing a web_input modular input configuration)
        """
        
        result = {}
        
        # Run the input
        try:
            web_input = WebInput(timeout=10)
        
            url_field = URLField( "url", "title", "preview" )
            selector_field = SelectorField( "selector", "title", "preview" )
            
            # Get the authentication information, if available
            username = None
            password = None
            
            if( 'password' in kwargs and 'username' in kwargs):
                username = kwargs['username']
                password = kwargs['password']
            
            include_empty_matches = False
            
            if 'include_empty_matches' in kwargs:
                include_empty_matches = util.normalizeBoolean(kwargs['include_empty_matches'], True)
            
            # Scrape the page
            result = WebInput.scrape_page( url_field.to_python(url), selector_field.to_python(selector), username=username, password=password, include_empty_matches=include_empty_matches )
            
        except FieldValidationException, e:
            cherrypy.response.status = 202
            return self.render_error_json(_(str(e)))
        
        except:
            cherrypy.response.status = 500
            return self.render_error_json(_("The request could not be completed"))
        
        # Return the information
        return self.render_json(result)