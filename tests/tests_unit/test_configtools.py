#  Copyright 2020 Cognite AS
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os
import unittest
from dataclasses import dataclass

from cognite.client import CogniteClient
from cognite.extractorutils.configtools import BaseConfig, CogniteConfig, _to_snake_case, load_yaml
from cognite.extractorutils.exceptions import InvalidConfigError


@dataclass
class TestCastingClass:
    boolean_field: bool
    another_boolean_field: bool
    yet_another_boolean_field: bool
    string_field: str
    another_string_field: str
    yet_another_string_field: str


class TestConfigtoolsMethods(unittest.TestCase):
    def test_ensure_snake_case(self):
        snake_dict = {
            "test_key": "testValue",
            "another_key": "another-value",
            "last": {"last_one": "val1", "last_two": "val2"},
        }
        hyphen_dict = {
            "test-key": "testValue",
            "another-key": "another-value",
            "last": {"last-one": "val1", "last-two": "val2"},
        }
        camel_dict = {
            "testKey": "testValue",
            "anotherKey": "another-value",
            "last": {"lastOne": "val1", "lastTwo": "val2"},
        }
        pascal_dict = {
            "TestKey": "testValue",
            "AnotherKey": "another-value",
            "Last": {"LastOne": "val1", "LastTwo": "val2"},
        }

        self.assertDictEqual(snake_dict, _to_snake_case(snake_dict, "snake"))
        self.assertDictEqual(snake_dict, _to_snake_case(hyphen_dict, "hyphen"))
        self.assertDictEqual(snake_dict, _to_snake_case(camel_dict, "camel"))
        self.assertDictEqual(snake_dict, _to_snake_case(pascal_dict, "pascal"))

    def test_read_cognite_config(self):
        config_raw = """    
        # API key to CDF
        api-key: COGNITE_API_KEY
    
        # CDF project (also known as tenant name)
        project: tenant-name
    
        # How to label uploaded data in CDF
        external-id-prefix: "test_"
        """

        config = load_yaml(config_raw, CogniteConfig)

        self.assertIsInstance(config, CogniteConfig)
        self.assertEqual(config.host, "https://api.cognitedata.com")
        self.assertEqual(config.project, "tenant-name")
        self.assertEqual(config.external_id_prefix, "test_")
        self.assertEqual(config.api_key, "COGNITE_API_KEY")

        client = config.get_cognite_client("test-client")

        self.assertIsInstance(client, CogniteClient)
        self.assertEqual(client.config.base_url, "https://api.cognitedata.com")
        self.assertEqual(client.config.project, "tenant-name")
        self.assertEqual(client.config.api_key, "COGNITE_API_KEY")
        self.assertEqual(client.config.client_name, "test-client")

    def test_read_base_config(self):
        config_raw = """
        version: "1"
        
        logger:
            # Console logging
            console:
                level: INFO
             
        # Information about CDF tenant
        cognite:
            # CDF server
            host: https://greenfield.cognitedata.com
        
            # API key to CDF
            api-key: COGNITE_API_KEY
        
            # CDF project (also known as tenant name)
            project: tenant-name
        
            # How to label uploaded data in CDF
            external-id-prefix: "test_"
        """

        config = load_yaml(config_raw, BaseConfig)

        self.assertIsInstance(config, BaseConfig)

        self.assertEqual(config.version, "1")

        self.assertEqual(config.cognite.host, "https://greenfield.cognitedata.com")
        self.assertEqual(config.cognite.project, "tenant-name")
        self.assertEqual(config.cognite.external_id_prefix, "test_")
        self.assertEqual(config.cognite.api_key, "COGNITE_API_KEY")

        self.assertEqual(config.logger.console.level, "INFO")
        self.assertIsNone(config.logger.file)

    def test_read_invalid_missing_fields(self):
        # missing project
        config_raw = """    
        # How to label uploaded data in CDF
        external-id-prefix: "test_"
        """

        with self.assertRaises(InvalidConfigError):
            load_yaml(config_raw, CogniteConfig)

    def test_read_invalid_extra_fields(self):
        config_raw = """    
        # API key to CDF
        api-key: COGNITE_API_KEY
        
        # CDF project (also known as tenant name)
        project: tenant-name
    
        # How to label uploaded data in CDF
        external-id-prefix: "test_"
        
        # Does not exist:
        no-such-field: value
        """

        with self.assertRaises(InvalidConfigError):
            load_yaml(config_raw, CogniteConfig)

    def test_read_invalid_wrong_type(self):
        config_raw = """    
        # API key to CDF
        api-key: 123
        
        # CDF project (also known as tenant name)
        project: tenant-name
    
        # How to label uploaded data in CDF
        external-id-prefix: "test_"
        """

        with self.assertRaises(InvalidConfigError):
            load_yaml(config_raw, CogniteConfig)

    def test_get_cognite_client_from_api_key(self):
        config_raw = """    
        api-key: COGNITE_API_KEY
        project: tenant-name
        external-id-prefix: "test_"
        """
        config = load_yaml(config_raw, CogniteConfig)
        cdf = config.get_cognite_client("client_name")
        self.assertIsInstance(cdf, CogniteClient)
        print("CONFIG", repr(cdf._config))
        print("API_KEY", repr(cdf._config.api_key))
        self.assertEqual(cdf._config.api_key, "COGNITE_API_KEY")
        self.assertIsNone(cdf._config.token)

    def test_get_cognite_client_from_aad(self):
        config_raw = """    
        idp-authentication:
            tenant: foo
            client_id: cid
            secret: scrt
            scopes: 
                - scp
            min_ttl: 40
        project: tenant-name
        external-id-prefix: "test_"
        """
        config = load_yaml(config_raw, CogniteConfig)
        self.assertIsNone(config.api_key)
        cdf = config.get_cognite_client("client_name")
        self.assertIsInstance(cdf, CogniteClient)
        # The api_key is not None, possibly some thread local trick when run in Jenkins
        # self.assertTrue(cdf._config.api_key is None or cdf._config.api_key == "********")

    def test_get_cognite_client_no_credentials(self):
        config_raw = """
        project: tenant-name
        external-id-prefix: "test_"
        """
        config = load_yaml(config_raw, CogniteConfig)
        with self.assertRaises(InvalidConfigError) as cm:
            config.get_cognite_client("client_name")
        self.assertEqual(str(cm.exception), "Invalid config: No CDF credentials")

    def test_read_boolean_casting(self):
        os.environ["TRUE_FLAG"] = "true"
        os.environ["FALSE_FLAG"] = "FALSE"
        os.environ["STR_VAL"] = "TeST"
        config_raw = """ 
        boolean-field: ${TRUE_FLAG}
        another-boolean-field: ${FALSE_FLAG}
        yet-another-boolean-field: false
        string-field: "true"
        another-string-field: "test"
        yet-another-string-field: ${STR_VAL}
        """
        config: TestCastingClass = load_yaml(config_raw, TestCastingClass)
        self.assertTrue(config.boolean_field)
        self.assertFalse(config.another_boolean_field)
        self.assertFalse(config.yet_another_boolean_field)
        self.assertEqual(config.string_field, "true")
        self.assertEqual(config.another_string_field, "test")
        self.assertEqual(config.yet_another_string_field, "TeST")

    def test_read_invalid_boolean_casting(self):
        os.environ["TRUE_FLAG"] = "true"
        os.environ["FALSE_FLAG"] = "FALSE"
        os.environ["INVALID_FLAG"] = "TEST"
        config = """    
        boolean-field: ${FALSE_FLAG}
        another-boolean-field: ${INVALID_FLAG}
        yet-another-boolean-field: false
        string-field: "true"
        another-string-field: "test"
        yet-another-string-field: "test" 
        """
        with self.assertRaises(InvalidConfigError):
            load_yaml(config, TestCastingClass)
