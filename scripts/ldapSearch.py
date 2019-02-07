#!/usr/bin/env python
import ldap
import sys

searchFilter = sys.argv[1]
#searchFilter = "uid=*%s*" % uidSearchStr

# first you must open a connection to the server
try:
    l = ldap.open("ldap.jpl.nasa.gov")
    # searching doesn't require a bind in LDAP V3.  If you're using LDAP v2, set the next line appropriately
    # and do a bind as shown in the above example.
    # you can also set this to ldap.VERSION2 if you're using a v2 directory
    # you should  set the next option to ldap.VERSION2 if you're using a v2 directory
    l.protocol_version = ldap.VERSION3
    #l.simple_bind_s('uid=gmanipon, ou=personnel, dc=dir, dc=jpl, dc=nasa, dc=gov','bogus')
except ldap.LDAPError as e:
    print(e)
    # handle error however you like

# The next lines will also need to be changed to support your search requirements and directory
baseDN = "ou=personnel,dc=dir,dc=jpl,dc=nasa,dc=gov"
searchScope = ldap.SCOPE_SUBTREE
# retrieve all attributes - again adjust to your needs - see documentation for more options
retrieveAttributes = None
#retrieveAttributes = ['displayName']

try:
    ldap_result_id = l.search(
        baseDN, searchScope, searchFilter, retrieveAttributes)
    result_set = []
    while 1:
        result_type, result_data = l.result(ldap_result_id, 0)
        if (result_data == []):
            break
        else:
            # here you don't have to append to a list
            # you could do whatever you want with the individual entry
            # The appending to list is just for illustration.
            if result_type == ldap.RES_SEARCH_ENTRY:
                result_set.append(result_data)
    # print result_set
except ldap.LDAPError as e:
    print(e)

if len(result_set) > 0:
    for result in result_set:
        print(("#" * 80))
        print((result[0][0]))
        for key in list(result[0][1].keys()):
            print(("%s: %s" % (key, '\n\t'.join(result[0][1][key]))))
        print(("#" * 80))
else:
    print("No entries found.")
