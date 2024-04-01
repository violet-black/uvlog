import logging

import pytest

import uvlog


class TestCompatibility:

    @pytest.mark.parametrize('logger', [logging, uvlog])
    def test_logging(self, logger):
        logger.debug('test message %s', 'test')
        logger.info('test message %s', 'test')
        logger.warning('test message %s', 'test')
        logger.error('test message %s', 'test')
        logger.critical('test message %s', 'test')

    @pytest.mark.parametrize('logger', [logging, uvlog])
    def test_get_logger(self, logger):
        logger = logger.getLogger('pytest')
        logger = logger.getChild('test')
        logger.info('test message')

    @pytest.mark.parametrize('logger', [logging, uvlog])
    def test_basic_config(self, logger):
        logger.basicConfig(level='DEBUG')
        logger.info('test message')

    @pytest.mark.parametrize('logger', [logging, uvlog])
    def test_basic_config_int(self, logger):
        logger.basicConfig(level=10)
        logger.info('test message')
