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
import ipaddress

def handler(context, inputs):

    ipam = IPAM(context, inputs)
    IPAM.do_get_ip_ranges = do_get_ip_ranges

    return ipam.get_ip_ranges()


def do_get_ip_ranges(self, auth_credentials, cert):
    username = auth_credentials["privateKeyId"]
    password = auth_credentials["privateKey"]
    hostname = self.inputs["endpoint"]["endpointProperties"]["hostName"]

    requests.packages.urllib3.disable_warnings()

    swis = SwisClient(hostname, username, password)
    result_ranges = []
    qResult = swis.query("SELECT DISTINCT GroupID AS id, FriendlyName AS name, Address AS addressSpaceId, CIDR AS subnetPrefixLength, Comments AS description, i.CustomProperties.Gateway as gatewayAddress, i.CustomProperties.DNS_Servers as dnsServers, i.CustomProperties.Site_ID AS siteId FROM IPAM.GroupNode i WHERE GroupTypeText LIKE 'Subnet' AND i.CustomProperties.VRA_Range = TRUE")
    for range in qResult['results']:
      network = ipaddress.ip_network(str(range['addressSpaceId']) + '/' + str(range['subnetPrefixLength']))
      range['ipVersion'] = 'IPv' + str(network.version)
      range['startIPAddress'] = str(network[10])
      range['endIPAddress'] = str(network[-6])
      range['dnsServerAddresses'] = [server.strip() for server in str(range['dnsServers']).split(',')]
      range['tags'] = [{
        "key": "Site",
        "value": range['siteId']
      }]
      result_ranges.append(range)

    result = {
      "ipRanges": result_ranges
    }

    return result
