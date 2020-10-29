"""
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
from datetime import datetime
import ipaddress
import socket

def handler(context, inputs):

    ipam = IPAM(context, inputs)
    IPAM.do_allocate_ip = do_allocate_ip

    return ipam.allocate_ip()

def do_allocate_ip(self, auth_credentials, cert):
    username = auth_credentials["privateKeyId"]
    password = auth_credentials["privateKey"]
    hostname = self.inputs['endpoint']['endpointProperties']['hostName']

    global swis
    swis = SwisClient(hostname, username, password)
    requests.packages.urllib3.disable_warnings()

    allocation_result = []
    try:
        resource = self.inputs["resourceInfo"]
        for allocation in self.inputs["ipAllocations"]:
            allocation_result.append(allocate(resource, allocation, self.context, self.inputs["endpoint"]))
    except Exception as e:
        try:
            rollback(allocation_result)
        except Exception as rollback_e:
            logging.error(f"Error during rollback of allocation result {str(allocation_result)}")
            logging.error(rollback_e)
        raise e

    assert len(allocation_result) > 0
    return {
        "ipAllocations": allocation_result
    }

def allocate(resource, allocation, context, endpoint):

    last_error = None
    for range_id in allocation["ipRangeIds"]:

        logging.info(f"Allocating from range {range_id}")
        try:
            return allocate_in_range(range_id, resource, allocation, context, endpoint)
        except Exception as e:
            last_error = e
            logging.error(f"Failed to allocate from range {range_id}: {str(e)}")

    logging.error("No more ranges. Raising last error")
    raise last_error


def allocate_in_range(range_id, resource, allocation, context, endpoint):
    if int(allocation['size']) == 1:
        vmName = resource['name']
        owner = resource['owner']
        
        logging.info(f"Grabbing details about IP range ID {range_id}...")
        qNetwork = swis.query(f"SELECT DISTINCT Address, CIDR FROM IPAM.GroupNode WHERE GroupTypeText LIKE 'Subnet' AND GroupID = {range_id}")
        network = ipaddress.ip_network(f"{qNetwork['results'][0]['Address']}/{qNetwork['results'][0]['CIDR']}")
        maxOrdinal = network.num_addresses -5

        logging.info(f"Grabbing next available IPs...")
        qAddresses = swis.query(f"SELECT TOP 5 IpNodeId, IpAddress FROM IPAM.IPNode WHERE SubnetId = {range_id} AND IPOrdinal > 9 AND IPOrdinal < {maxOrdinal} AND Status = 2 AND LastSync IS NULL")
        for address in qAddresses['results']:
            ipAddress = address['IpAddress']
            nodeId = address['IpNodeId']
            if check_dns(ipAddress) == True:
                logging.info(f"Reserving IP address {ipAddress}...")
                uri = f'swis://localhost/Orion/IPAM.IPNode/IpNodeId={nodeId}'
                swis.invoke("IPAM.SubnetManagement", "ChangeIPStatus", ipAddress, "Reserved")
                swis.update(uri, Comments=f"Reserved by {owner} at {datetime.now()}.", DnsBackward=vmName)
                logging.info(f"Successfully reserved {ipAddress} for {vmName}.")
                result = {
                    "ipAllocationId": allocation['id'],
                    "ipRangeId": range_id,
                    "ipVersion": f"IPv{network.version}",
                    "ipAddresses": [ipAddress]
                }
                break
        return result
    
    else:
        # TODO: allocate continuous block of ips
        pass
    raise Exception("Not implemented")

## Rollback any previously allocated addresses in case this allocation request contains multiple ones and failed in the middle
def rollback(allocation_result):
    for allocation in reversed(allocation_result):
        logging.info(f"Rolling back allocation {str(allocation)}")
        ipAddresses = allocation.get("ipAddresses", None)
        for ipAddress in ipAddresses:
            swis.invoke("IPAM.SubnetManagement", "ChangeIPStatus", ipAddress, "Available")
    return

def check_dns(ipAddress):
    logging.info(f"Checking DNS for {ipAddress}...")
    try:
        socket.gethostbyaddr(ipAddress)
    except Exception as e:
        if '[Errno 1]' in str(e):
            # No PTR record for that IP
            logging.info(f"Great news: No DNS record found.")
            return True
        else:
            logging.info(f"Encountered an error: {e}.")
            return False
    else:
        # There might be a conflict
        return False
        logging.info(f"Uh-oh, found a conflicting DNS record.")
