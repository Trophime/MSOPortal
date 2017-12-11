""" MSO4SC views module """

import time
import json
import yaml
import requests

from urllib.parse import urlparse
from portal import settings

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse
# from django.contrib.auth import login, authenticate
# from django.contrib import messages
# from django.views.decorators.clickjacking import xframe_options_exempt

# from social_django.models import UserSocialAuth
from social_django.utils import load_strategy

from cloudify_rest_client import CloudifyClient
from cloudify_rest_client.exceptions import CloudifyClientError
from cloudify_rest_client.exceptions \
    import DeploymentEnvironmentCreationPendingError
from cloudify_rest_client.exceptions \
    import DeploymentEnvironmentCreationInProgressError
WAIT_FOR_EXECUTION_SLEEP_INTERVAL = 3


def _get_fiware_token(user, from_url):
    social = user.social_auth.get(provider='fiware')
#    if int(time.time()) - social.extra_data['auth_time'] > 3600:
#        #    strategy = load_strategy()
#        #    social.refresh_token(strategy)
#        return (False, '/oauth/login/fiware?next=' + from_url)
    return (True, social.extra_data['access_token'])


@login_required
def index(request):
    social_user = request.user.social_auth.get(uid=request.user.username)
    # access_token = social_user.access_token
    valid, data = _get_fiware_token(
        request.user, request.get_full_path())
    if valid:
        access_token = data
    else:
        return redirect(data)
    token_expires_in = 3600 - \
        (int(time.time()) - social_user.extra_data['auth_time'])
    m, s = divmod(token_expires_in, 60)
    h, m = divmod(m, 60)
    str_expires_in = str(m) + ' minutes and ' + str(s) + ' seconds.'
    if h > 0:
        str_expires_in = '1 hour'
    extra_data = social_user.extra_data

    return render(request, 'home.html', {'access_token': access_token +
                                         ', expires in ' + str_expires_in,
                                         'extra_data': extra_data})


@login_required
def marketplace_logIn(request):
    if 'marketplace' not in request.session:
        request.session['marketplace'] = False

    if request.session['marketplace']:
        return redirect('/marketplace')

    return redirect(settings.MARKETPLACE_URL + '/login')


@login_required
def marketplace_loggedIn(request):
    request.session['marketplace'] = True
    return redirect('/marketplace')


@login_required
def marketplace(request):
    if 'marketplace' not in request.session:
        request.session['marketplace'] = False

    if not request.session['marketplace']:
        return redirect('/marketplaceLogIn')

    context = {'marketplace_url': settings.MARKETPLACE_URL}
    return render(request, 'marketplace.html', context)


@login_required
def datacatalogue_logIn(request):
    if 'datacatalogue' not in request.session:
        request.session['datacatalogue'] = False

    if request.session['datacatalogue']:
        return redirect('/datacatalogue')

    return redirect(settings.DATACATALOGUE_URL + '/user/login')


@login_required
def datacatalogue_loggedIn(request):
    request.session['datacatalogue'] = True
    return redirect('/datacatalogue')


@login_required
def datacatalogue(request):
    if 'datacatalogue' not in request.session:
        request.session['datacatalogue'] = False

    if not request.session['datacatalogue']:
        return redirect('/datacatalogueLogIn')

    context = {'datacatalogue_url': settings.DATACATALOGUE_URL}
    return render(request, 'datacatalogue.html', context)


@login_required
def experimentstool(request):
    context = {
        'datacatalogue_url': settings.DATACATALOGUE_URL,
        'marketplace_url': settings.MARKETPLACE_URL,
    }

    return render(request, 'experimentstool.html', context)


def get_products(request):
    valid, data = _get_fiware_token(request.user, request.get_full_path())
    if valid:
        access_token = data
    else:
        # FIXME Cross-Origin Request Blocked: The Same Origin Policy disallows
        # reading the remote resource at https://account.lab.fiware.org/oauth2/
        #   authorize?client_id=859680e0c8cb4c65b5d2d6fb99ef1595&redirect_uri=
        #   http://localhost:8000/oauth/complete/fiware/&state=eXpNpKJ5jqsZoOB
        #   cm0X1hLcmaSCNoa3E&response_type=code.
        #   (Reason: CORS header ‘Access-Control-Allow-Origin’ missing).
        return redirect(data)
    headers = {"Authorization": "bearer " + access_token}
    url = settings.MARKETPLACE_URL + \
        "/DSProductCatalog/api/catalogManagement/v2/productSpecification"

    text_data = requests.request("GET", url, headers=headers).text
    json_data = json.loads(text_data)

    request.session['products'] = json_data
    return JsonResponse(json_data, safe=False)


@login_required
def upload_blueprint(request):
    if 'products' not in request.session:
        return JsonResponse({'error': 'No products loaded'})

    products = request.session['products']
    product_id = request.POST.get('product', None)
    if not product_id:
        return JsonResponse({'error': 'No product id provided'})

    mso4sc_id = request.POST.get('mso_id', None)
    if not mso4sc_id or mso4sc_id == '':
        # TODO validation
        return JsonResponse({'error': 'No mso4sc id provided'})

    product = None
    for p in products:
        if p["id"] == product_id:
            product = p
            break
    if not product:
        return JsonResponse({'error': 'Product not found'})

    blueprint_path = None
    for pc in product['productSpecCharacteristic']:
        if pc['name'] == 'BLUEPRINT_PATH':
            blueprint_path = pc['productSpecCharacteristicValue'][0]['value']
            break
    if not blueprint_path:
        return JsonResponse({'error': 'The product does not have a \'BLUEPRINT_PATH\' charasteristic'})

    return JsonResponse(_upload_blueprint(blueprint_path, mso4sc_id))


def get_blueprints(request):
    client = _get_client()
    try:
        blueprints = client.blueprints.list().items
    except CloudifyClientError as e:
        print(e)
        return JsonResponse({'error': str(e)})

    request.session['blueprints'] = blueprints
    return JsonResponse({'blueprints': blueprints})


def get_datasets(request):
    url = settings.DATACATALOGUE_URL + \
        "/api/3/action/package_list"

    text_data = requests.request("GET", url).text
    json_data = json.loads(text_data)
    if not json_data["success"]:
        return JsonResponse([], safe=False)  # TODO(emepetres) manage errors

    request.session['datasets'] = json_data["result"]
    return JsonResponse(json_data["result"], safe=False)


def get_dataset_info(request):
    if 'datasets' not in request.session:
        return {'error': 'No datasets loaded'}

    datasets = request.session['datasets']
    dataset_index = int(request.GET.get('dataset', -1))

    if dataset_index >= len(datasets) or dataset_index < 0:
        return JsonResponse({'error': 'Bad dataset index provided'})

    dataset = datasets[dataset_index]

    url = settings.DATACATALOGUE_URL + \
        "/api/rest/dataset/" + dataset

    text_data = requests.request("GET", url).text
    if text_data == "Not found":
        return JsonResponse(None)  # TODO(emepetres) manage errors

    json_data = json.loads(text_data)
    return JsonResponse(json_data, safe=False)


@login_required
def create_deployment(request):
    if 'blueprints' not in request.session:
        return {'error': 'No blueprints loaded'}
    if 'datasets' not in request.session:
        return {'error': 'No datasets loaded'}

    blueprints = request.session['blueprints']
    datasets = request.session['datasets']

    blueprint_index = int(request.POST.get('blueprint_index', -1))
    dataset_index = int(request.POST.get('dataset_index', -1))
    inputs_file = request.FILES['deployment_inputs']
    inputs_data = inputs_file.read().decode("utf-8").replace('\r\n', '\n')
    inputs = yaml.load(inputs_data)
    deployment_id = request.POST.get('deployment_id', None)

    if blueprint_index >= len(blueprints) or blueprint_index < 0:
        return JsonResponse({'error': 'Bad blueprint index provided'})
    if dataset_index >= len(datasets) or dataset_index < 0:
        return JsonResponse({'error': 'Bad dataset index provided'})
    if not deployment_id or deployment_id is '':
        return JsonResponse({'error': 'No deployment provided'})

    blueprint = blueprints[blueprint_index]['id']
    dataset = datasets[dataset_index]  # TODO

    return JsonResponse(_create_deployment(blueprint, deployment_id, inputs))


def get_deployments(request):
    client = _get_client()
    try:
        deployments = client.deployments.list().items
    except CloudifyClientError as e:
        print(e)
        return JsonResponse({'error': str(e)})

    request.session['deployments'] = deployments
    return JsonResponse({'deployments': deployments})


@login_required
def install_deployment(request):
    return _execute_deployment(request, _install_deployment)


@login_required
def run_deployment(request):
    return _execute_deployment(request, _run_deployment)


@login_required
def uninstall_deployment(request):
    return _execute_deployment(request, _uninstall_deployment)


@login_required
def destroy_deployment(request):
    return _execute_deployment(request, _destroy_deployment)


def _execute_deployment(request, operation):
    if 'deployments' not in request.session:
        return {'error': 'No deployments loaded'}

    deployments = request.session['deployments']

    deployment_index = int(request.POST.get('deployment_index', -1))

    if deployment_index is None:
        return JsonResponse({'error': 'No deployment provided'})

    if deployment_index >= len(deployments) or deployment_index < 0:
        return JsonResponse({'error': 'Bad deployment index provided'})

    deployment = deployments[deployment_index]['id']
    return JsonResponse(operation(deployment))


@login_required
def remove_blueprint(request):
    if 'blueprints' not in request.session:
        return {'error': 'No blueprints loaded'}

    blueprints = request.session['blueprints']

    blueprint_index = int(request.POST.get('blueprint_index', -1))

    if blueprint_index is None:
        return JsonResponse({'error': 'No blueprint provided'})

    if blueprint_index >= len(blueprints) or blueprint_index < 0:
        return JsonResponse({'error': 'Bad blueprint index provided'})

    blueprint = blueprints[blueprint_index]['id']
    return JsonResponse(_remove_blueprint(blueprint))


def _get_client():
    client = CloudifyClient(host=settings.ORCHESTRATOR_HOST,
                            username=settings.ORCHESTRATOR_USER,
                            password=settings.ORCHESTRATOR_PASS,
                            tenant=settings.ORCHESTRATOR_TENANT)
    return client


def _upload_blueprint(path, blueprint_id):
    is_url = bool(urlparse(path).scheme)

    client = _get_client()
    try:
        if is_url:
            blueprint = client.blueprints.publish_archive(path, blueprint_id)
        else:
            blueprint = client.blueprints.upload(path, blueprint_id)
    except CloudifyClientError as e:
        print(e)
        return {'error': str(e)}

    return {'blueprint': blueprint}


def _create_deployment(blueprint_id, development_id, inputs, retries=3):
    client = _get_client()
    try:
        deployment = client.deployments.create(
            blueprint_id,
            development_id,
            inputs=inputs,
            skip_plugins_validation=True
        )
    except (DeploymentEnvironmentCreationPendingError,
            DeploymentEnvironmentCreationInProgressError) as e:
        if (retries > 0):
            time.sleep(WAIT_FOR_EXECUTION_SLEEP_INTERVAL)
            return _create_deployment(blueprint_id, development_id, inputs,
                                      retries - 1)
        print(e)
        return {'error': str(e)}
    except CloudifyClientError as e:
        print(e)
        return {'error': str(e)}
    return {'deployment': deployment}


def _install_deployment(development_id):
    return _execute_workflow(development_id, 'install')


def _run_deployment(development_id):
    return _execute_workflow(development_id, 'run_jobs')


def _uninstall_deployment(development_id):
    return _execute_workflow(development_id, 'uninstall')


def _execute_workflow(development_id, workflow):
    client = _get_client()
    try:
        execution = client.executions.start(development_id, workflow)
    except CloudifyClientError as e:
        print(e)
        return {'execution': None, 'error': str(e)}
    return {'execution': execution, 'error': None}


def _destroy_deployment(development_id, force=False):
    client = _get_client()
    try:
        deployment = client.deployments.delete(
            development_id, ignore_live_nodes=force)
    except CloudifyClientError as e:
        print(e)
        return {'deployment': None, 'error': str(e)}
    return {'deployment': deployment, 'error': None}


def _remove_blueprint(blueprint_id):
    client = _get_client()
    try:
        blueprint = client.blueprints.delete(blueprint_id)
    except CloudifyClientError as e:
        print(e)
        return {'blueprint': None, 'error': str(e)}

    return {'blueprint': blueprint, 'error': None}
