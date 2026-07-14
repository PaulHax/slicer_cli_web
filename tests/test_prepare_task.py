import json
import os

import cherrypy
import pytest
from girder.api import rest
from girder.models.token import Token

from slicer_cli_web.cli_utils import as_model, get_cli_parameters
from slicer_cli_web.prepare_task import prepare_task


@pytest.mark.plugin('slicer_cli_web')
@pytest.mark.parametrize('stringForwardInputs', [False, True])
def test_output_references_carry_run_uuid(server, admin, folder, file, stringForwardInputs):
    # Make a request to allow there to be some lingering context so that the
    # girder client transforms can be constructed outside of a request.
    server.request('/system/version')
    rest.setCurrentUser(admin)
    cherrypy.request.params['token'] = Token().createToken(admin)['_id']

    xmlpath = os.path.join(os.path.dirname(__file__), 'data', 'ExampleSpec.xml')
    clim = as_model(open(xmlpath, 'rb').read())
    index_params, opt_params, _ = get_cli_parameters(clim)

    if stringForwardInputs:
        # Forward raw id strings instead of loading Girder models, as happens
        # for inputs declared with reference="_girder_id_".
        for param in index_params + opt_params:
            if param.channel != 'output' and param.typ == 'image':
                param.reference = '_girder_id_'

    params = {
        'inputImageFile': str(file['_id']),
        'secondImageFile': str(file['_id']),
        'outputStainImageFile_1_folder': str(folder['_id']),
        'outputStainImageFile_1': 'sample1.png',
        'outputStainImageFile_2_folder': str(folder['_id']),
        'outputStainImageFile_2': 'sample2.png',
        'stainColor_1': '[0.5, 0.5, 0.5]',
        'stainColor_2': '[0.2, 0.3, 0.4]',
        'returnparameterfile_folder': str(folder['_id']),
        'returnparameterfile': 'output.data',
    }
    token = Token().createToken(admin)
    reference = {'slicer_cli_web': {'title': 't', 'image': 'i', 'name': 'n'}}
    _, result_hooks, primary_input_name = prepare_task(
        params, admin, token, index_params, opt_params, True, reference)

    if stringForwardInputs:
        assert primary_input_name is None
    else:
        assert primary_input_name == 'Sample'
    assert reference['uuid']
    refs = [json.loads(hook.upload_kwargs['reference']) for hook in result_hooks]
    # indexed output, optional output, and return parameter file
    assert len(refs) == 3
    assert all(ref['uuid'] == reference['uuid'] for ref in refs)
