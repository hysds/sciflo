import os
import sys
import re
import json
import copy
from urllib.request import urlopen
from urllib.parse import urlparse

from .xmlUtils import getXmlEtree

VIEW_RE = re.compile('^(.+?)\((.*)\)$')


def parseView(view):
    """Return view type and arg dict."""

    argDict = {}
    match = VIEW_RE.search(view)
    if not match:
        raise RuntimeError("Failed to parse view: %s" % view)
    typ = match.group(1)
    for param in match.group(2).split(','):
        if '=' in param:
            key, val = param.split('=')
        else:
            key, val = param, None
        argDict[key] = val
    return typ, argDict


def getTabConfig(sfl):
    """Parse sciflo document and return tab configuration in JSON format."""

    # parse doc
    sflStr = urlopen(sfl).read()
    rt, nsDict = getXmlEtree(sflStr)

    # get global inputs
    globalInputsNames = []
    globalInputsConfig = {}
    globalInputs = rt.xpath('./sf:flow/sf:inputs/*', nsDict)
    for input in globalInputs:
        globalInputsNames.append(input.tag)
        globalInputsConfig[input.tag] = {
            'type': input.get('type', None),
            'view': input.get('view', None),
            'group': input.get('group', None),
            'value': input.text
        }

    # get processes
    optionalTabs = []
    optionalOperators = []
    itemConfig = {}
    readyToRun = []
    groupNames = ['Setup']
    groupsConfig = {
        'Setup': {
            'procs': [],
            'argsConfigs': [],
            'globalInputs': []
        }
    }
    globalInputsUsed = {}
    processes = rt.xpath('./sf:flow/sf:processes/*', nsDict)
    prevGroup = None
    altSetupTitle = None
    for process in processes:
        # print process.get('id')

        # process args
        argsConfig = []
        ready = True
        for arg in process.xpath('./sf:inputs/*', nsDict):
            val = None
            tagText = arg.get('from', arg.text)
            if tagText is None:
                tagText = ''

            # collect args connected to global input
            if tagText.startswith('@#inputs.'):
                val = tagText
            elif tagText == '@#inputs':
                val = '@#inputs.%s' % arg.tag
            elif arg.tag in globalInputsNames:
                val = '@#inputs.%s' % arg.tag  # match implicits
            else:
                # check if links to a previous process, either @#previous or @#<process name>
                if tagText.startswith('@#'):
                    ready = False
            if val is not None:
                argsConfig.append([arg.tag, val])

        # collect groups
        group = process.get('group', None)
        if group is None:
            if ready:
                group = 'Setup'
            else:
                group = prevGroup
        if group:
            if ready and group != 'Setup':
                if altSetupTitle is None:
                    altSetupTitle = group
                group = 'Setup'
            if group not in groupNames:
                groupNames.append(group)
                groupsConfig[group] = {
                    'procs': [process.get('id')],
                    'argsConfigs': []
                }
            else:
                groupsConfig[group]['procs'].append(process.get('id'))

        if ready:
            readyToRun.append(process.get('id'))

        # loop over remove from previous tab/items
        argsConfigCopy = copy.deepcopy(argsConfig)
        for procTag, argVal in argsConfigCopy:
            argTag = argVal.split('.')[1]
            globalOverrideGroup = globalInputsConfig[argTag]['group']
            if globalOverrideGroup and globalOverrideGroup in groupsConfig:
                newGroup = groupsConfig[globalOverrideGroup]
                if process.get('id') in newGroup['procs']:
                    newIdx = newGroup['procs'].index(process.get('id'))
                    if len(newGroup['argsConfigs']) != len(newGroup['procs']):
                        newGroup['argsConfigs'].append([[procTag, argVal]])
                    else:
                        newGroup['argsConfigs'][newIdx].append(
                            [procTag, argVal])
                    argsConfig.remove([procTag, argVal])
                else:
                    newGroup['procs'].append(process.get('id'))
                    newGroup['argsConfigs'].append([[procTag, argVal]])
                globalInputsUsed[argTag] = [
                    globalOverrideGroup, process.get('id')]
            else:
                if argTag in globalInputsUsed:
                    # remove from previous argConfig in groupsConfig
                    oldGroup, oldId = globalInputsUsed[argTag]
                    oldIdx = groupsConfig[oldGroup]['procs'].index(oldId)
                    oldArgConfig = groupsConfig[oldGroup]['argsConfigs'][oldIdx]
                    rmIdx = None
                    for x, oldTagVal in enumerate(oldArgConfig):
                        if oldTagVal[0] == procTag:
                            rmIdx = x
                            break
                    if rmIdx is not None:
                        oldArgConfig.pop(rmIdx)
                globalInputsUsed[argTag] = [group, process.get('id')]
        groupsConfig[group]['argsConfigs'].append(argsConfig)
        prevGroup = group

        # get tab and item name
        if '/' in group:
            tabName, itemName = group.split('/')
        else:
            tabName, itemName = group, None

        # collect optional tabs and operators
        if process.get('optional', '').lower() == 'true':
            optionalTabs.append(tabName)
            optionalOperators.append(group)

        # collect paletteIcons
        paletteIcon = process.get('paletteIcon', None)
        if paletteIcon is not None:
            itemConfig.setdefault(group, {'paletteIcon': paletteIcon})

    #print >>sys.stderr, "groupNames:", groupNames
    # print >>sys.stderr, "#" * 80
    #print >>sys.stderr, "groupsConfig:", json.dumps(groupsConfig, indent=2)
    # print >>sys.stderr, "#" * 80

    # create tab config
    tabNames = []
    tabConfig = {}
    for group in groupNames:
        groupConfig = groupsConfig[group]

        # get tab and item name
        if '/' in group:
            tabName, itemName = group.split('/')
        else:
            tabName, itemName = group, None
        # print >>sys.stderr, "#" * 80
        ##print >>sys.stderr, "group:", group

        # loop over procs and add to global inputs
        for i in range(len(groupConfig['procs'])):
            proc = groupConfig['procs'][i]
            argConfigList = groupConfig['argsConfigs'][i]
            ##print >>sys.stderr, "  proc:", proc
            for tagName, inputName in argConfigList:
                inputName = inputName.split('.')[1]
                ##print >>sys.stderr, "    inputName:", inputName

                # check if global input has special tab
                giGroup = globalInputsConfig[inputName]['group']
                if giGroup is not None:
                    # get tab and item name
                    if '/' in giGroup:
                        giTabName, giItemName = giGroup.split('/')
                    else:
                        if giGroup == 'Setup':
                            giTabName, giItemName = giGroup, None
                        else:
                            giTabName, giItemName = giGroup, inputName
                else:
                    giTabName, giItemName = tabName, itemName
                ##print >>sys.stderr, "      giTabName, giItemName:", giTabName, giItemName

                if giTabName not in tabNames:
                    if giTabName != tabName:
                        # insert special tab before this tab
                        tabNames.insert(-1, giTabName)
                    else:
                        tabNames.append(giTabName)
                    tabConfig[giTabName] = {
                        'items': [giItemName],
                        'globalInputs': [inputName]
                    }
                else:
                    ##print >>sys.stderr, "      inputName, tabConfig:", inputName, tabConfig[giTabName]['globalInputs']
                    if inputName not in tabConfig[giTabName]['globalInputs']:
                        tabConfig[giTabName]['items'].append(giItemName)
                        tabConfig[giTabName]['globalInputs'].append(inputName)
                    else:
                        # if global input is listed under a different item, extract it to Setup
                        giIndex = tabConfig[giTabName]['globalInputs'].index(
                            inputName)
                        origItem = tabConfig[giTabName]['items'][giIndex]
                        if origItem != giItemName:
                            tabConfig['Setup']['items'].append(None)
                            tabConfig['Setup']['globalInputs'].append(
                                inputName)
                            tabConfig[giTabName]['globalInputs'].pop(giIndex)
                            tabConfig[giTabName]['items'].pop(giIndex)
                        #print >>sys.stderr, "giIndex, origItem:", giIndex, origItem
    #print >>sys.stderr, "tabConfig:", tabNames, json.dumps(tabConfig, indent=2)
    # print >>sys.stderr, "#" * 80

    # cvo config
    id = rt.xpath('./sf:flow', nsDict)[0].get('id')
    titleElts = rt.xpath('./sf:flow/sf:title/text()', nsDict)
    if len(titleElts) == 0:
        title = id
    else:
        title = titleElts[0]
    cvoConfig = {
        'id': id,
        'title': title,
        'sciflo': os.path.basename(urlparse(sfl)[2]),
        'tabs': []
    }
    for tabName in tabNames:
        tab = {
            'name': tabName.lower(),
            'title': tabName,
            'validationUrl': 'services/validateSetup',
            'dbName': ('%s_%s' % (id, tabName)).replace(' ', '_'),
            'items': []
        }

        # set tab as form if no items were configured
        isFormTab = False
        if None in tabConfig[tabName]['items']:
            for item in tabConfig[tabName]['items']:
                if item is not None:
                    raise RuntimeError(
                        "Cannot have a non-item argument with item configurations.")
            isFormTab = True

        # create form tab or item tab
        if isFormTab:
            for gi in tabConfig[tabName]['globalInputs']:
                giConfig = globalInputsConfig[gi]
                name = gi
                if giConfig['view'] == None:
                    tab['items'].append({
                        'type': 'textfield',
                        'name': gi,
                        'value': giConfig['value'],
                        'fieldLabel': gi,
                        'sflGlobalInput': gi
                    })
                else:
                    itemType, argDict = parseView(giConfig['view'])
                    ##print >>sys.stderr, "itemType, argDict:", itemType, argDict
                    if itemType == 'checkboxgroup':
                        tab['items'].append({
                            'name': name,
                            'title': name,
                            'paletteIcon': argDict.get('paletteIcon', None),
                            'items': {'url': argDict.get('url')},
                            'sflGlobalInput': gi
                        })
                    else:
                        if itemType == 'datetime':
                            itemType = 'textfield'
                        if itemType == 'bbox':
                            if 'cmp' in argDict:
                                name = argDict['cmp']
                            itemType = 'textfield'
                        tab['items'].append({
                            'type': itemType,
                            'name': name,
                            'value': giConfig['value'],
                            'fieldLabel': argDict.get('fieldLabel', gi),
                            'sflGlobalInput': gi
                        })
        else:
            itemDict = {}
            for i, gi in enumerate(tabConfig[tabName]['globalInputs']):
                item = tabConfig[tabName]['items'][i]
                giConfig = globalInputsConfig[gi]
                name = gi
                #print >>sys.stderr, "name, item:", name, item
                if item not in itemDict:
                    if giConfig['view'] == None:
                        #print >>sys.stderr, "no view"
                        itemDict[item] = {
                            'name': item,
                            'title': item,
                            'paletteIcon': None,
                            'items': [{
                                'name': name,
                                'fieldLabel': name,
                                'value': giConfig['value'],
                                'sflGlobalInput': gi
                            }]
                        }
                    else:
                        itemType, argDict = parseView(giConfig['view'])
                        #print >>sys.stderr, "itemType, argDict:", itemType, argDict
                        if itemType == 'checkboxgroup':
                            itemDict[item] = {
                                'name': item,
                                'title': item,
                                'paletteIcon': argDict.get('paletteIcon', None),
                                'items': {'url': argDict.get('url')},
                                'sflGlobalInput': gi
                            }
                        else:
                            if itemType == 'datetime':
                                itemType = 'textfield'
                            if itemType == 'bbox':
                                if 'cmp' not in argDict:
                                    raise RuntimeError(
                                        "Cannot find component spec.")
                                name = argDict['cmp']
                                itemType = 'textfield'
                            itemDict[item] = {
                                'name': item,
                                'title': item,
                                'paletteIcon': argDict.get('paletteIcon', None),
                                'items': [{
                                    'name': name,
                                    'fieldLabel': argDict.get('fieldLabel', name),
                                    'value': giConfig['value'],
                                    'sflGlobalInput': gi
                                }]
                            }
                else:
                    #print >>sys.stderr, "Got here"
                    if giConfig['view'] == None:
                        itemType, argDict = 'textfield', {}
                    else:
                        itemType, argDict = parseView(giConfig['view'])
                    #print >>sys.stderr, "itemType, argDict:", itemType, argDict
                    if 'paletteIcon' in argDict:
                        itemDict[item]['paletteIcon'] = argDict['paletteIcon']
                    if itemType == 'checkboxgroup':
                        itemDict[item]['items'].append({
                            'name': name,
                            'fieldLabel': argDict.get('fieldLabel', name),
                            'url': argDict.get('url'),
                            'sflGlobalInput': gi
                        })
                    else:
                        if itemType == 'datetime':
                            itemType = 'textfield'
                        if itemType == 'bbox':
                            if 'cmp' not in argDict:
                                raise RuntimeError(
                                    "Cannot find component spec.")
                            name = argDict['cmp']
                            itemType = 'textfield'
                        itemDict[item]['items'].append({
                            'name': name,
                            'fieldLabel': argDict.get('fieldLabel', name),
                            'value': giConfig['value'],
                            'sflGlobalInput': gi
                        })
            finishedItems = []
            for item in tabConfig[tabName]['items']:
                if item not in finishedItems:
                    tab['items'].append(itemDict[item])
                    finishedItems.append(item)

        # append tab; if setup, assign to setupTab
        if tabName == 'Setup':
            # add setup palette icon
            tab['paletteIcon'] = 'scripts/iearth/imgs/z00gboxb.png'
            cvoConfig['setupTab'] = tab
        else:
            cvoConfig['tabs'].append(tab)
    #print >>sys.stderr, "tabConfig:", tabNames, json.dumps(tabConfig, indent=2)
    # print >>sys.stderr, "#" * 80

    # check for missing tabs/operators and optional tabs
    for x, groupName in enumerate(groupNames):
        groupConfig = groupsConfig[groupName]

        # get tab and item name
        if '/' in groupName:
            tabName, itemName = groupName.split('/')
        else:
            tabName, itemName = groupName, None
        if tabName == 'Setup':
            continue
        foundTab = False
        foundItem = False
        cvoTabNames = []
        for cvoTabCfg in cvoConfig['tabs']:
            if cvoTabCfg['title'] not in cvoTabNames:
                cvoTabNames.append(cvoTabCfg['title'])
            if cvoTabCfg['title'] == tabName:
                foundTab = cvoTabCfg
                for itemCfg in cvoTabCfg['items']:
                    if itemCfg['title'] == itemName:
                        foundItem = itemCfg
                        break
                if foundItem:
                    break
        if foundItem is False:
            ##print >>sys.stderr, "Not found:", groupName
            if foundTab is False:
                tab = {
                    'name': tabName.lower(),
                    'title': tabName,
                    'validationUrl': 'services/validateSetup',
                    'items': [
                        {
                            'name': itemName,
                            'title': itemName,
                            'items': [
                                {
                                    'fieldLabel': 'Nothing to be configured for this operator.',
                                    'xtype': 'checkbox',
                                    'boxLabel': itemName,
                                    'labelSeparator': '',
                                    'checked': True,
                                    'hidden': True,
                                    'name': tabName.lower(),
                                    'sflGlobalInput': 'do_%s' % itemName
                                }
                            ]
                        }
                    ]
                }
                if len(groupNames)-1 == x:
                    cvoConfig['tabs'].append(tab)
                else:
                    if groupNames[x+1].split('/')[0] in cvoTabNames:
                        cvoConfig['tabs'].insert(cvoTabNames.index(
                            groupNames[x+1].split('/')[0]), tab)
                    else:
                        cvoConfig['tabs'].append(tab)
            else:
                foundTab['items'].append({
                    'name': itemName,
                    'title': itemName,
                    'items': [
                        {
                            'fieldLabel': 'Nothing to be configured for this operator.',
                            'xtype': 'checkbox',
                            'boxLabel': itemName,
                            'labelSeparator': '',
                            'checked': True,
                            'hidden': True,
                            'name': tabName.lower(),
                            'sflGlobalInput': 'do_%s' % itemName
                        }
                    ]
                })
        else:
            # add do_* item if optional
            if groupName in optionalOperators:
                foundItem['items'].append({
                    'fieldLabel': '',
                    'xtype': 'checkbox',
                    'boxLabel': 'do_%s' % itemName,
                    'labelSeparator': '',
                    'checked': True,
                    'hidden': True,
                    'name': tabName.lower(),
                    'sflGlobalInput': 'do_%s' % itemName
                })
    #print >>sys.stderr, "cvoConfig:", json.dumps(cvoConfig, indent=2)
    # print >>sys.stderr, "#" * 80

    # add missing global inputs to setup
    misItems = []
    for gi in globalInputsNames:
        if gi not in globalInputsUsed:
            print("%s not used" % gi, file=sys.stderr)
            giConfig = globalInputsConfig[gi]
            name = gi
            if giConfig['view'] == None:
                misItems.append({
                    'type': 'textfield',
                    'name': gi,
                    'value': giConfig['value'],
                    'fieldLabel': gi,
                    'sflGlobalInput': gi
                })
            else:
                itemType, argDict = parseView(giConfig['view'])
                ##print >>sys.stderr, "itemType, argDict:", itemType, argDict
                if itemType == 'checkboxgroup':
                    misItems.append({
                        'name': name,
                        'title': name,
                        'paletteIcon': argDict.get('paletteIcon', None),
                        'items': {'url': argDict.get('url')},
                        'sflGlobalInput': gi
                    })
                else:
                    if itemType == 'datetime':
                        itemType = 'textfield'
                    if itemType == 'bbox':
                        if 'cmp' in argDict:
                            name = argDict['cmp']
                        itemType = 'textfield'
                    misItems.append({
                        'type': itemType,
                        'name': name,
                        'value': giConfig['value'],
                        'fieldLabel': argDict.get('fieldLabel', gi),
                        'sflGlobalInput': gi
                    })
    cvoConfig['setupTab']['items'].extend(misItems)

    # set tab enablers
    finalTabNames = []
    firstOptionalSet = False
    enabler = 'setup'
    lastEnabler = 'setup'
    for x, cvoTabCfg in enumerate(cvoConfig['tabs']):
        if x > 0:
            if cvoTabCfg['title'] in optionalTabs:
                if firstOptionalSet:
                    enabler = lastEnabler
                else:
                    enabler = cvoConfig['tabs'][x-1]['name']
                    firstOptionalSet = True
            else:
                enabler = cvoConfig['tabs'][x-1]['name']
        cvoTabCfg['enabledBy'] = enabler
        lastEnabler = enabler

    # set execution enabler and paletteIcons
    allTabs = [cvoConfig['setupTab']]
    allTabs.extend(cvoConfig['tabs'])
    for cvoTabCfg in allTabs:
        if lastEnabler == cvoTabCfg['name']:
            cvoTabCfg['enableExecute'] = True
        if cvoTabCfg['name'] == 'setup':
            continue
        for item in cvoTabCfg['items']:
            if 'title' not in item:
                item['title'] = item['name']
            groupItem = '%s/%s' % (cvoTabCfg['title'], item['title'])
            if groupItem in itemConfig:
                item['paletteIcon'] = itemConfig[groupItem]['paletteIcon']

    # set alternate setup title
    if altSetupTitle is not None:
        cvoConfig['setupTab']['title'] = altSetupTitle

    return json.dumps(cvoConfig, indent=2)
