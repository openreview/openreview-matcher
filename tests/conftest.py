'''
Defines pytest fixtures that maintain a persistent state
(in relation to the test openreview server) between tests.
'''

import os

import pytest
import matcher
import openreview

from helpers.TestUtil import TestUtil

# pylint:disable=unused-argument
@pytest.fixture
def test_util(scope="session"):
    '''
    A pytest fixture that instantiates a TestUtil object.
    This fixture is passed into each test and persists across
    scopes according to the `scope` argument.
    '''
    or_baseurl = 'http://localhost:3000'
    flask_app_test_client = matcher.app.test_client()
    flask_app_test_client.testing = True
    return TestUtil.get_instance(or_baseurl, flask_app_test_client)


# pylint:disable=unused-argument
@pytest.fixture
def or_client(scope="session"):
    '''
    A pytest fixture that instantiates an openreview.Client object.
    '''
    client = openreview.Client(
        username=os.getenv('OPENREVIEW_USERNAME'),
        password=os.getenv('OPENREVIEW_PASSWORD'),
        baseurl='http://localhost:3000')

    return client
