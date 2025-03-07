Basic Solarwinds IPAM integration plugin for vRA(C) 8.x
============

> [!IMPORTANT]
> This project is no longer maintained. Feel free to use it as a starting point for your own efforts, but I won't be updating it any further.

This contains the Python source files I used to create a basic IPAM integration so our vRA 8.x environment could leverage Solarwinds IPAM. See https://code.vmware.com/web/sdk/1.0.0/vmware-vrealize-automation-third-party-ipam-sdk to obtain the necessary SDK and https://docs.vmware.com/en/VMware-Cloud-services/1.0/ipam_integration_contract_reqs.pdf for the technical details. 

This expects several custom properties to exist in Solarwinds for each IPAM-managed subnet to aid with assigning the correct gateway address, DNS servers, and site identifiers, as well as to limit the scope so we don't retrieve EVERY subnet that IPAM knows about:
- `DNS_Servers`: comma-separated list of IPs
- `Gateway`: single IP address for the default route
- `Site_ID`: 3-character identifier
- `vRA_Range`: boolean; true if you want the subnet to be used by vRA

Or you can edit `src/main/python/get_ip_ranges/source.py` to remove/change this requirement.
