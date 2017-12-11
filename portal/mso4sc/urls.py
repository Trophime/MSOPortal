from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='home'),
    url(r'^marketplaceLogIn/$', views.marketplace_logIn,
        name='marketplace_logIn'),
    url(r'^marketplaceLoggedIn/$', views.marketplace_loggedIn,
        name='marketplace_loggedIn'),
    url(r'^marketplace/$', views.marketplace, name='marketplace'),
    url(r'^datacatalogueLogIn/$', views.datacatalogue_logIn,
        name='datacatalogue_logIn'),
    url(r'^datacatalogueLoggedIn/$', views.datacatalogue_loggedIn,
        name='datacatalogue_loggedIn'),
    url(r'^datacatalogue/$', views.datacatalogue, name='datacatalogue'),
    url(r'^experimentstool/$', views.experimentstool, name='experimentstool'),
    url(r'^experimentstool/_get_products$',
        views.get_products, name='_get_products'),
    url(r'^experimentstool/_upload_application$',
        views.upload_blueprint, name='_upload_application'),
    url(r'^experimentstool/_get_blueprints$',
        views.get_blueprints, name='_get_blueprints'),
    url(r'^experimentstool/_get_datasets$',
        views.get_datasets, name='_get_datasets'),
    url(r'^experimentstool/_get_dataset_info$',
        views.get_dataset_info, name='_get_dataset_info'),
    url(r'^experimentstool/_deploy_application$',
        views.create_deployment, name='_deploy_application'),
    url(r'^experimentstool/_get_deployments$',
        views.get_deployments, name='_get_deployments'),
    url(r'^experimentstool/_install_deployment$',
        views.install_deployment, name='_install_deployment'),
    url(r'^experimentstool/_run_deployment$',
        views.run_deployment, name='_run_deployment'),
    url(r'^experimentstool/_uninstall_deployment$',
        views.uninstall_deployment, name='_uninstall_deployment'),
    url(r'^experimentstool/_destroy_deployment$',
        views.destroy_deployment, name='_destroy_deployment'),
    url(r'^experimentstool/_remove_blueprint$',
        views.remove_blueprint, name='_remove_blueprint'),
]
