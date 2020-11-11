"""
Modified by John Bowdre to support Solarwinds IPAM
Initial release: 11/10/2020

Copyright (c) 2020 VMware, Inc.

This product is licensed to you under the Apache License, Version 2.0 (the "License").
You may not use this product except in compliance with the License.

This product may include a number of subcomponents with separate copyright notices
and license terms. Your use of these subcomponents is subject to the terms and
conditions of the subcomponent's license, as noted in the LICENSE file.
"""

import requests
from vra_ipam_utils.ipam import IPAM
import logging
from orionsdk import SwisClient

def handler(context, inputs):

    ipam = IPAM(context, inputs)
    IPAM.do_deallocate_ip = do_deallocate_ip

    return ipam.deallocate_ip()

def do_deallocate_ip(self, auth_credentials, cert):
    username = auth_credentials["privateKeyId"]
    password = auth_credentials["privateKey"]
    hostname = self.inputs['endpoint']['endpointProperties']['hostName']

    global swis
    swis = SwisClient(hostname, username, password)
    requests.packages.urllib3.disable_warnings()

    deallocation_result = []
    for deallocation in self.inputs["ipDeallocations"]:
        deallocation_result.append(deallocate(self.inputs["resourceInfo"], deallocation))

    assert len(deallocation_result) > 0
    return {
        "ipDeallocations": deallocation_result
    }

def deallocate(resource, deallocation):
    ip_range_id = deallocation["ipRangeId"]
    ip = deallocation["ipAddress"]
    resource_id = resource["id"]

    logging.info(f"Deallocating ip {ip} from range {ip_range_id}")
    swis.invoke("IPAM.SubnetManagement", "ChangeIPStatus", ip, "Available")
    return {
        "ipDeallocationId": deallocation["id"],
        "message": "Success"
    }
