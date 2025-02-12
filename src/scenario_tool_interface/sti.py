#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
import time
import enum


url = "https://staging-api.dance4water.org/api"
dance_url = "https://staging-sql.dance4water.org/resultsdb/"


class AccessLevel(enum.Enum):
    DEMO = 1
    PARTICIPANT = 2
    CONSULTANT = 3
    ADMIN = 4
    SUPERADMIN = 5

def db_name(simulation_id):
    return simulation_id


class ScenarioToolInterface:

    def __init__(self, api_url="https://staging-api.dance4water.org/api", results_url="https://staging-sql.dance4water.org/resultsdb/"):
        self.api_url = api_url
        self.results_url = results_url

        self.authenticated = False
        self.token = None

    def login(self, username, password):
        """
        Get access token

        :param username: registered user name (email address)
        :param password: top secret password
        :return: access token
        """
        counter = 0
        while True:
            r = requests.post(self.api_url + "/user/login/", json={'username': username,
                                                          'password': password})
            counter += 1
            if r.status_code == 200:
                self.token = r.json()["access_token"]
                self.authenticated = True
                return
            if counter > 4:
                raise Exception(f"Unable to login status {r.status_code}")

            else:
                time.sleep(2)

    def _get(self, url):

        if not self.authenticated or self.token is None:
            raise Exception(f"User not authenticated, GET FAILED, {url}")

        headers = {"Authorization": "Bearer " + self.token}
        return requests.get(url, headers=headers)

    def _put(self, url, data={}):

        if not self.authenticated or self.token is None:
            raise Exception(f"User not authenticated, PUT FAILED, {url}")

        headers = {"Authorization": "Bearer " + self.token}
        return requests.put(url, json=data, headers=headers)


    def _post(self, url, data={}):

        if not self.authenticated or self.token is None:
            raise Exception(f"User not authenticated, {url}")

        headers = {"Authorization": "Bearer " + self.token}
        return requests.post(url, json=data, headers=headers)


    def run_query(self, scenario_id, query):
        """
        Run a query on the scenario spatialite database. The database supports SQLite and Spatialite commands
        Only read access is supported! To find out which data are stored in the database read the dynamind_table_definitions

        :param scenario_id: scenario id
        :param query: SQL query
        :type scenario_id: int
        :type query str
        :return: query result
        :rtype: dict
        """

        simulation_id = self.get_database_id(scenario_id)
        data = {'db_name': db_name(simulation_id),
                'query': query}
        r = self._post(self.results_url, data)

        if r.status_code == 200:
            result = r.json()
            return result
        raise Exception(f"Unable to run query {r.status_code}")

    def add_node(self, node_data):
        return self._post(self.api_url + "/sm_node", node_data)

    def update_sm_node(self, node_id, node_data):
        return self._post(self.api_url + "/sm_node/" + str(node_id) + "/versions", node_data)

    def add_model(self, name, src):
        return self._post(self.api_url + "/models", {"name": name, "model_src": src})

    def get_models(self):
        return self._get(self.api_url + "/models/")

    def get_database_id(self, scenario_id):
        """
        Returns database ID to run data analysis

        :param scenario_1_id: scenario id
        :return: data base id needed for query
        """
        r = self.get_simulations(scenario_id)
        if r.status_code != 200:
            raise Exception(f"Unable to obtain scenarios {r.status_code}")

        sims = r.json()

        for s in sims["simulations"]:
            sim = json.loads(s)
            if sim["simulation_type"] == "PERFORMANCE_ASSESSMENT":
                return sim["id"]



    def create_project(self):
        """
        Creates a new project

        :return: project id
        :rtype: int
        """

        r = self._post(self.api_url + "/projects")

        if r.status_code == 200:
            return r.json()["id"]

        raise Exception(f"Creation of project failed {r.status_code}")

    def get_project(self, project):
        return self._get(self.api_url + "/projects/" + str(project))

    def get_projects(self):
        return self._get(self.api_url + "/projects/")

    def update_project(self, project, data):
        return self._put(self.api_url + "/projects/" + str(project), data)

    def get_assessment_models(self):
        return self._get(self.api_url + "/assessment_models")

    def get_assessment_model(self, model_name):
        """
        Returns assessment model id

        :param model_name: Model Name. Currently supported are Land Surface Temperature and Target
        :type model_name: str
        :return: model_id
        :rtype: int
        """
        r = self._get(self.api_url + "/assessment_models")

        if not r.status_code == 200:
            raise Exception(f"Could not get assessment model {r.status_code}")

        models = r.json()["assessment_models"]
        model_id = None

        for model in models:
            if model["name"] == model_name:
                model_id = model["id"]
                break

        if model_id is None:
            raise Exception(f"Could not find ' {model_name}")

        return model_id

    def set_project_assessment_models(self, project, models):
        return self._put(self.api_url + "/projects/" + str(project) + "/models", models)

    def create_scenario(self, project, parent, name="initialised model"):
        """
        Creates a new scenario. The provides the shell for the new scenarios. Scenario are derived from the base line
        or any other scenario in the project. To modify the environment workflow may be defined and executed.

        :param project: project id
        :param parent: parent scenario id
        :param name: name of scenario
        :type int
        :type int
        :type str
        :return: scenario id
        ":rtype: int
        """
        data = {"project_id": project, "name": name}
        if parent is not None:
            data["parent"] = parent

        r = self._post(self.api_url + "/scenario/", data)

        if r.status_code == 200:
            return r.json()["id"]

        raise Exception(f"Unable to create scenario {r.status_code}")


    def set_scenario_workflow(self, scenario_id, node_data):
        """
        Set the workflow for a scenario. The workflow is defined by a series of nodes defined by the node_data
        The node_data have following structure

        .. code-block::

            [{
               name: node_id,
               area: geojson_id,
               parameters: {

                parameter.value = 1,
                paramter2.value = 2,

               }
            },
            ...
            ]

        The nodes in the workflow are executed as defined in the data structure

        :param scenario_id: scenario id
        :param node_data: node data see above
        :type scenario_id: int
        :type node_data: list

        """

        r = self._post(self.api_url + "/scenario/" + str(scenario_id) + "/nodes", node_data)
        if r.status_code == 200:
            return

        raise Exception(f"Something went wrong when adding the nodes {r.status_code} {r.json()}")

    def get_scenario_workflow_nodes(self):

        return self._get(self.api_url + "/sm_node/")

    def upload_geojson(self, geojson, project_id, name="casestudyarea"):
        """
        Upload a geojson file and return id

        :param geojson: geojson file
        :param project_id: project the node will be assigned to
        :param name: added option to set name of geojson file default is set to casestudyarea

        :type geojson: str
        :type name: str
        :type project_id: int
        :return: geojson id
        :rtype: int
        """

        if 'name' in geojson: del geojson['name']

        r = self._post(self.api_url + "/geojson/", {"project_id": project_id, "geojson": geojson, "name":name})

        if r.status_code == 200:
            return r.json()["id"]

        raise Exception(f"Unable to upload file {r.status_code}")


    def get_region(self, region_name):
        """
        Returns region currently supported is Melbourne

        :param region: region id
        :return: region id
        """

        r = self._get(self.api_url + "/regions/")
        if not r.status_code == 200:
            raise Exception(f"Unable to get region {r.status_code}")
        regions = r.json()
        melbourne_region_id = None
        for region in regions:
            if region["name"].lower() == region_name:
                melbourne_region_id = region["id"]
                break

        if melbourne_region_id is None:
            raise Exception(f"Could not find ' {region_name}")

        return melbourne_region_id

    def get_regions(self):
        return self._get(self.api_url + "/regions/")


    def execute_scenario(self, scenario, queue="default"):
        """

        :param scenario: id of scenario to be executed
        :param queue: optional parameter to define queue
        :rtype: str
        :rtype: str
        """
        return self._post(f'{self.api_url}/scenario/{scenario}/execute?queue={queue}')


    def get_geojsons(self, project):
        return self._get(self.api_url + "/geojson/" + str(project))


    def check_status(self, scenario):
        """
        Return status of current simulation.

        returns:

        .. code-block::

            {
               status: status code (int),
               status_text: status description
            }

            // CREATED = 1
            // BASE_IN_QUEUE = 2
            // BASE_RUNNING = 3
            // BASE_COMPLETE = 4
            // PA_IN_QUEUE = 5
            // PA_RUNNING = 6
            // PA_COMPLETE = 7
            // COMPLETE = 8

        :param scenario: scenario id
        :type scenario: int
        :return: scenario status
        :rtype: dict

        """

        r= self._get(self.api_url + "/scenario/" + str(scenario) + "/status")
        if r.status_code != 200:
            raise Exception(f"Unable to get status {r.status_code}")
        return r.json()


    def get_scenario(self, scenario):
        return self._get(self.api_url + "/scenario/" + str(scenario))


    def get_simulations(self, scenario):
        return self._get(self.api_url + "/scenario/" + str(scenario) + "/simulations")


    def upload_dynamind_model(self, name, filename):
        """
        Uploads a new model to the server

        :param name: model name
        :param filename: dynamind file
        :type str
        :return: model_id
        :rtype: int
        """
        with open(filename, 'r') as file:
            data = file.read().replace('\n', '')

        r = self.add_model(name, data)

        model_id = r.json()["model_id"]

        return model_id


    def show_node_versions(self, node_id):
        return self._get(self.api_rul + "/sm_node/" + str(node_id))


    def create_node(self, filename, model_id=None, access_level=AccessLevel.SUPERADMIN.value):
        """
        Create a new node

        :param filename: point to json file containing the node description
        :param model_id: model id in json file will be replaced by this. If not set model_id from json file
        :param access_level: access level of node
        :type str
        :type int
        :type int
        :return: node_id
        :rtype: int
        """
        with open(filename) as json_file:
            node_data = json.load(json_file)

        if model_id is not None:
            node_data["models"][0]["id"] = model_id
            node_data["access_level"] = access_level
        r = self.add_node(node_data)

        if r.status_code == 200:
            result = r.json()
            return result["node_id"]
        raise Exception(f"Unable to add node {r.status_code}")


    def update_node(self, node_id, filename, model_id=None, access_level=AccessLevel.SUPERADMIN.value):
        """
        Update an existing node

        :param node_id: id of node
        :param filename: point to json file containing the node description
        :param model_id: model id in json file will be replaced by this. If not set model_id from json file
        :param access_level: access level of node
        :type str
        :type str
        :type int
        :type int
        :return: node_id
        :rtype: int
        """
        with open(filename) as json_file:
            node_data = json.load(json_file)

        if model_id is not None:
            node_data["models"][0]["id"] = model_id
            node_data["access_level"] = access_level
        r = self.update_sm_node(node_id, node_data)

        if r.status_code == 200:
            result = r.json()
            return result["node_version_id"]
        raise Exception(f"Unable to update node {r.status_code}")


    def set_node_access_level(self, node_id, access_level):
        """
        Set the access level of the parent node

        :param node_id: node id
        :param access_level: access level (see enum)
        :type node_id: int
        :type access_level: int
        """
        r = self._post(f"{self.api_url}/sm_node/{node_id}",{"access_level": access_level})
        if r.status_code == 200:
            return
        raise Exception(f"Could not update access level node {r.status_code}")


    def deactivate_node(self, node_id):
        """
        Deactivate node

        :param token: access token
        :param node_id: node id
        :type token: str
        :type node_id: int
        """
        r = self._post(f"{self.api_url}/sm_node/{node_id}", {"active": False})
        if r.status_code == 200:
            return
        raise Exception(f"Could not deactivate node {r.status_code}")


    def get_baseline(self, project_id):
        """
        Get a projects baseline scenario id

        :param project_id: Project ID
        :type project_id: int
        :return: baseline scenario id
        :rtype: int
        """
        r = self.get_project(project_id)
        scenarios = r.json()["scenarios"]
        scene = next(item for item in scenarios if item["parent"] is None)
        baseline_id = scene["id"]
        return baseline_id


    def get_city_boundary(self, project_id):
        """
        Return a cities geojson boundary id

        :param token: Access token
        :param project_id: project ID
        :type token: str
        :type project_id: int
        :return: geojson boundary id
        :rtype: int
        """

        r = self.get_geojsons(project_id)
        geojsons = r.json()
        geojson_city_id = geojsons["geojsons"][0]["id"]
        return geojson_city_id


    def show_nodes(self):
        """
        Prints list of available nodes

        :param token: Access token
        :type token: str
        """
        r = self.get_scenario_workflow_nodes()
        if not r.status_code == 200:
            raise Exception(f"Could not get scenario workflow nodes")

        smnodes = r.json()["scenario_maker_nodes"]
        for node in smnodes:
            print(node["id"], node["name"])


    def get_nodes(self):
        """
        Return list of available nodes

        :param token: Access token
        :type token: str

        :return: returns a dict of all scenario
        :rtype: dict
        """
        r = self.get_scenario_workflow_nodes()
        if not r.status_code == 200:
            raise Exception(f"Could not get scenario workflow nodes")

        smnodes = r.json()["scenario_maker_nodes"]

        return smnodes


    def show_scenarios(self, project_id):
        """
        Prints a list of the scenarios in a project

        :param token: Access token
        :param project_id: project id
        :type token: str
        :type project_id: int
        """
        r = self.get_project(project_id)
        if not r.status_code == 200:
            raise Exception(f"Could not get scenario workflow nodes {r.status_code}")

        scenarios = r.json()["scenarios"]
        for s in scenarios:
            print(s["id"], s["status"], s["name"])


    def get_scenarios(self, project_id):
        """
        Get a list of scenarios in a project

        :param token: Access token
        :param project_id: project ID
        :type str
        :type int
        :return: returns a dict of all scenario
        :rtype: dict
        """
        r = self.get_project(project_id)
        if not r.status_code == 200:
            raise Exception(f"Could not get scenario workflow nodes {r.status_code}")

        scenarios = r.json()["scenarios"]
        return scenarios


    def show_log(self, scenario_id):
        """
        Print scenario log file

        :param scenario_id: scenario id
        :type scenario_id: int
        """
        r = self.get_simulations(scenario_id)

        if not r.status_code == 200:
            raise Exception(f"Could not get scenario log {r.status_code}")

        sims = r.json()

        for s in sims["simulations"]:
            database_id = json.loads(s)["id"]
        for s in sims["simulation_intances"]:
            print(json.loads(s)["id"],  json.loads(s)["progress"], json.loads(s)["heartbeat"], json.loads(s)["log"])

        return database_id


    def get_node_id(self, name):
        """
        Return node id to be used in simulation. If multiple nodes with the same id are identified the first node
        belonging to the user is returned first

        :param token: access token
        :param name: node name
        :return: node_id
        :rtype int
        """
        nodes = self.get_nodes()
        filtered_nodes = []
        for n in nodes:
            if n['name'] == name:
                filtered_nodes.append(n)
        if len(filtered_nodes) == 0:
            raise Exception(f"Node  {name} not found")

        if len(filtered_nodes) == 1:
            return filtered_nodes[0]["id"]
        # if multiple nodes return the one the user owns
        for n in filtered_nodes:
            if n["creator"] == self.get_my_status()["user_id"]:
                return n["id"]

        return filtered_nodes[0]["id"]






    def create_assessment_model(self, filename, model_id=None):
        """
        Creates a new assessment model and a default version tagged as 0.0.1
        the data must be of the shape:

        :param token: Access token
        :param filename: filename of json file (see below)
        :param model_id: dynamind model id
        :type token: str
        :type filename: str
        :type model_id: int

        .. code-block::

            {
               name: "some name",
               description: "some desc",

               //optionally add assessment model stage of development
               //1 = ALPHA
               //2 = BETA
               //3 = UNDER DEVELOPMENT
               //default is 3
               stage: 2
               //must specify one of:
               model_id: <model_id> //by default will use the active version of this model
               model_version_id: <model_version_id> //if present will use this model version id
            }

        returns:

        .. code-block::

            {
              assessment_model_id: <the id of the new assessment model>,
              assessment_model_version_id: <id of the new default version>
            }

        """

        with open(filename) as json_file:
            node_data = json.load(json_file)

        if model_id is not None:
            node_data["model_id"] = model_id

        r = self._post(self.api_url + "/assessment_models", node_data)

        if r.status_code == 200:
            result = r.json()
            return result["assessment_model_id"]
        raise Exception(f"Unable to create assessment model {r.status_code}")


    def update_assessment_model(self, assessment_model_id, filename, model_id):
        """
        Creates a new assessment model and a default version tagged as 0.0.1
        the data must be of the shape:

        :param token: access token
        :param assessment_model_id: assessment model id to be updated
        :param filename: filename of json file (see below)
        :param model_id: dynamind model id
        :type token: str
        :type assessment_model_id: int
        :type filename: str
        :type model_id: int

        .. code-block::

            {
               name: "some name",
               description: "some desc",

               //optionally add assessment model stage of development
               //1 = ALPHA
               //2 = BETA
               //3 = UNDER DEVELOPMENT
               //default is 3
               stage: 2
               //must specify one of:
               model_id: <model_id> //by default will use the active version of this model
               model_version_id: <model_version_id> //if present will use this model version id
            }

        returns:

        .. code-block::

            {
              assessment_model_id: <the id of the new assessment model>,
              assessment_model_version_id: <id of the new default version>
            }

        """
        with open(filename) as json_file:
            node_data = json.load(json_file)

        if model_id is not None:
            node_data["model_id"] = model_id

        print(f"{self.api_url}/assessment_models/{assessment_model_id}/versions")
        r = self._post(f"{url}/assessment_models/{assessment_model_id}/versions", node_data)
        if r.status_code == 200:
            result = r.json()
            return result["assessment_model_version_id"]
        raise Exception(f"Unable to update assessment model {r.status_code}")


    def get_project_databases(self, project_id, folder=".", scenario_id = None):
        """
        Download project databases. Databases will be downloaded into folder/project_id.zip
        For larger projects it is recommended to defined the scenario_id to be downloaded. Otherwise the download might fail
        :param token: access token
        :param project_id: project id
        :param folder: folder
        :param scenario_id: scenario_id
        :type token: str
        :type project_id: int
        :type folder: str
        :type scenario_id: int
        """


        if scenario_id:
            r = self._get(f"{self.api_url}/projects/{project_id}/data?scenario={scenario_id}")
        else:
            r = requests._get(f"{self.api_url}/projects/{project_id}/data")
        if r.status_code == 200:
            if scenario_id:
                open(f"{folder}/{project_id}-{scenario_id}.zip", 'wb').write(r.content)
            else:
                open(f"{folder}/{project_id}.zip", 'wb').write(r.content)
            return
        raise Exception(f"Something went wrong while downloading the folder {r.status_code} {r.json()}")


    def get_my_status(self):
        """
        Get user status
        :param token: access token
        :return: dict with project status
        """
        r = self._get(f"{self.api_url}/user/status/")
        if r.status_code == 200:
            return r.json()

        raise Exception(f"Something when downloading status {r.status_code} {r.json()}")
