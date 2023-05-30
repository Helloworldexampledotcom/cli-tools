from __future__ import annotations

import argparse
import json
import os
import pathlib
from tempfile import NamedTemporaryFile
from typing import List
from unittest import mock

import pytest
from googleapiclient import discovery
from oauth2client.service_account import ServiceAccountCredentials

from codemagic.firebase.resource_managers.release_manager import FirebaseReleaseManager
from codemagic.firebase.resources import Release
from codemagic.firebase.resources.identifiers import AppIdentifier
from codemagic.tools.firebase_app_distribution import FirebaseAppDistribution
from codemagic.tools.firebase_app_distribution.argument_types import CredentialsArgument
from codemagic.tools.firebase_app_distribution.arguments import FirebaseArgument
from codemagic.tools.firebase_app_distribution.errors import FirebaseError

credentials_argument = FirebaseArgument.FIREBASE_SERVICE_ACCOUNT_CREDENTIALS
project_id_argument = FirebaseArgument.PROJECT_ID


@pytest.fixture
def mock_releases() -> List[Release]:
    mock_response_path = pathlib.Path(__file__).parent / 'mocks' / 'firebase_releases.json'
    releases_response = json.loads(mock_response_path.read_text())
    return [Release(**release) for release in releases_response]


@pytest.fixture(autouse=True)
def register_args(cli_argument_group):
    for arg in FirebaseAppDistribution.CLASS_ARGUMENTS:
        arg.register(cli_argument_group)


@pytest.fixture()
def namespace_kwargs():
    ns_kwargs = {
        credentials_argument.key: CredentialsArgument('{"type":"service_account"}'),
        project_id_argument.key: '228333310124',
    }
    for arg in FirebaseAppDistribution.CLASS_ARGUMENTS:
        if not hasattr(arg.type, 'environment_variable_key'):
            continue
        os.environ.pop(arg.type.environment_variable_key, None)
    return ns_kwargs


def test_missing_credentials_arg(namespace_kwargs):
    namespace_kwargs[credentials_argument.key] = None
    cli_args = argparse.Namespace(**dict(namespace_kwargs.items()))

    with pytest.raises(argparse.ArgumentError) as exception_info:
        FirebaseAppDistribution.from_cli_args(cli_args)

    message = str(exception_info.value)
    assert credentials_argument.key.upper() in message
    if hasattr(credentials_argument.type, 'environment_variable_key'):
        assert credentials_argument.type.environment_variable_key in message
    assert ','.join(credentials_argument.flags) in message


def test_invalid_credentials_from_env(namespace_kwargs):
    os.environ[CredentialsArgument.environment_variable_key] = 'invalid credentials'
    namespace_kwargs[credentials_argument.key] = None
    cli_args = argparse.Namespace(**dict(namespace_kwargs.items()))
    with pytest.raises(argparse.ArgumentError) as exception_info:
        FirebaseAppDistribution.from_cli_args(cli_args)
    assert str(exception_info.value) == \
           "argument --credentials/-c: Provided value 'invalid credentials' is not a valid JSON encoded object"


def test_credentials_invalid_path(namespace_kwargs):
    os.environ[CredentialsArgument.environment_variable_key] = '@file:this-is-not-a-file'
    namespace_kwargs[credentials_argument.key] = None
    cli_args = argparse.Namespace(**dict(namespace_kwargs.items()))
    with pytest.raises(argparse.ArgumentError) as exception_info:
        FirebaseAppDistribution.from_cli_args(cli_args)
    assert str(exception_info.value) == 'argument --credentials/-c: File "this-is-not-a-file" does not exist'


@mock.patch('codemagic.tools.firebase_app_distribution.firebase.FirebaseClient')
def test_read_private_key(mock_firebase_api_client, namespace_kwargs):
    namespace_kwargs[credentials_argument.key] = CredentialsArgument('{"type":"service_account"}')
    _ = FirebaseAppDistribution.from_cli_args(argparse.Namespace(**namespace_kwargs))
    mock_firebase_api_client.assert_called_once_with({'type': 'service_account'})


@pytest.mark.parametrize(
    'configure_variable', [
        lambda filename, ns_kwargs: os.environ.update(
            {credentials_argument.type.environment_variable_key: f'@file:{filename}'},
        ),
        lambda filename, ns_kwargs: ns_kwargs.update(
            {credentials_argument.key: CredentialsArgument(f'@file:{filename}')},
        ),
    ],
)
@mock.patch('codemagic.tools.firebase_app_distribution.firebase.FirebaseClient')
def test_private_key_path_arg(mock_firebase_api_client, configure_variable, namespace_kwargs):
    with NamedTemporaryFile(mode='w') as tf:
        tf.write('{"type":"service_account"}')
        tf.flush()
        namespace_kwargs[credentials_argument.key] = None
        configure_variable(tf.name, namespace_kwargs)

        _ = FirebaseAppDistribution.from_cli_args(argparse.Namespace(**namespace_kwargs))
        mock_firebase_api_client.assert_called_once_with({'type': 'service_account'})


@pytest.mark.parametrize(
    'configure_variable', [
        lambda ns_kwargs: os.environ.update(
            {credentials_argument.type.environment_variable_key: '@env:CREDENTIALS'},
        ),
        lambda ns_kwargs: ns_kwargs.update(
            {credentials_argument.key: CredentialsArgument('@env:CREDENTIALS')},
        ),
    ],
)
@mock.patch('codemagic.tools.firebase_app_distribution.firebase.FirebaseClient')
def test_private_key_env_arg(mock_firebase_api_client, configure_variable, namespace_kwargs):
    os.environ['CREDENTIALS'] = '{"type":"service_account"}'
    namespace_kwargs[credentials_argument.key] = None
    configure_variable(namespace_kwargs)

    _ = FirebaseAppDistribution.from_cli_args(argparse.Namespace(**namespace_kwargs))
    mock_firebase_api_client.assert_called_once_with({'type': 'service_account'})


@pytest.fixture
def app_identifier():
    return AppIdentifier('228333310124', '1:228333310124:ios:5e439e0d0231a788ac8f09')


@pytest.fixture
def mock_firebase(app_identifier):
    return FirebaseAppDistribution({'type': 'service_account'}, app_identifier.project_id)


@pytest.fixture(autouse=True)
def mock_service_account():
    with mock.patch.object(ServiceAccountCredentials, 'from_json_keyfile_dict', return_value=None):
        yield


@pytest.fixture(autouse=True)
def mock_discovery_service():
    with mock.patch.object(discovery, 'build', return_value=mock.Mock):
        yield


@pytest.fixture
def mock_api_releases_list(mock_releases, app_identifier):
    with mock.patch.object(FirebaseReleaseManager, 'list', return_value=mock_releases) as mock_releases_list:
        yield mock_releases_list


def test_list_releases(mock_firebase, mock_api_releases_list, mock_releases, app_identifier):
    releases = mock_firebase.list_releases(app_identifier.app_id)
    mock_api_releases_list.assert_called_once_with(app_identifier, FirebaseReleaseManager.OrderBy.create_time_desc, 25)
    assert releases == mock_releases


def test_list_releases_with_limit(mock_firebase, mock_api_releases_list, mock_releases, app_identifier):
    mock_firebase.list_releases(app_identifier.app_id, limit=1)
    mock_api_releases_list.assert_called_once_with(app_identifier, FirebaseReleaseManager.OrderBy.create_time_desc, 1)


def test_get_latest_build_version(mock_firebase, mock_api_releases_list, app_identifier):
    build_number = mock_firebase.get_latest_build_version(app_identifier.app_id)
    mock_api_releases_list.assert_called_once_with(app_identifier, limit=1)
    assert build_number == 71


def test_get_latest_build_version_no_releases(mock_firebase, app_identifier):
    with mock.patch.object(FirebaseReleaseManager, 'list', return_value=[]) as mock_api_releases_list:
        with pytest.raises(FirebaseError):
            mock_firebase.get_latest_build_version(app_identifier.app_id)
    mock_api_releases_list.assert_called_once_with(app_identifier, limit=1)
