#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Name:        submit_sciflo.cgi
# Purpose:     Submit sciflo for execution.
#
# Author:      Gerald Manipon
#
# Created:     Thu Jul 27 11:10:57 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import cgi
from string import Template
import sciflo
import sys
from StringIO import StringIO
import urllib2
import os
import re
import types
import lxml.etree
import pageTemplate
from tempfile import mkdtemp
import cjson

from sciflo.utils import sanitizeHtml
from sciflo.utils.interfaceUtils import getTabConfig, parseView

#turn on script debugging in browser
#import cgitb; cgitb.enable()

#config file
configFile = None

#templates
spacesStr = '&nbsp;' * 3

formDataTpl = Template('''
<label for="${field}-id"><b>$field</b></label>:$spaces<font color="blue">$value</font><br/>
<b>type</b>:$spaces<font color="green">$tp</font><br/>''')

uploadScifloTpl = Template('''
<a id="main" name="main"></a>
<form enctype="multipart/form-data" name="uploadScifloDoc" method="POST">
<span>Execute sciflo:$spaces</span>
<span><input name="scifloStr" type="file" size="20"/></span>
<span><input type="submit" name="submit" value="submitSciflo" /></span>
</span>
</form>
<div id="formStatus"></div>''')

inputFormTpl = Template('''
<script type="text/javascript">

  /* xpath evaluator */
  function xpath(aNode, aExpr) {
      var xpe = new XPathEvaluator();
      var nsResolver = xpe.createNSResolver(aNode.ownerDocument == null ?
        aNode.documentElement : aNode.ownerDocument.documentElement);
      var result = xpe.evaluate(aExpr, aNode, nsResolver, 0, null);
      var found = [];
      var res;
      while (res = result.iterateNext()) { found.push(res); }
      return found;
  }

  /* input form validator */
  function validateForm(t) {
      try {
          /* get form and sciflo xml dom nodes */
          var form = Ext.DomQuery.select('form[id=scifloInputForm]')[0];
          var scifloUrl = Ext.DomQuery.select('input[id=scifloStr]')[0].value;
          //console.log(scifloUrl);
          var scifloDoc = null;
          Ext.Ajax.request({
            url: scifloUrl,
            method: 'GET',
            success: function(r, o) { scifloDoc = r.responseXML; },
            failure: function(r, o) { Ext.Msg.alert('Error:', r.responseText); },
            async: false
          });
          //console.log(scifloDoc); 
          //console.log(xpath(scifloDoc, 'sf:sciflo/sf:flow/sf:inputs'));
    
          /* get global inputs from sciflo xml node */
          var inputs = xpath(scifloDoc, 'sf:sciflo/sf:flow/sf:inputs/*');
    
          /* validate the form input corresponding to each global input */
          var errorsFound = 0;
          var errorMsg = "";
          for (var i=0; i < inputs.length; i++) {
              var sflInput = inputs[i];
    
              /* get type and view */
              var sflType = sflInput.getAttribute('type');
              var sflView = sflInput.getAttribute('view');
    
              /* get form input */
              var formInputs = Ext.DomQuery.select('input[id=' + sflInput.tagName + '-id]', form);
              if (formInputs.length == 0) var formInputs = Ext.DomQuery.select('input[id=' + sflInput.tagName + ']', form);
              if (sflView && /^datetime/i.test(sflView)) { //special case for ISODateTime widget
                  var formInputs = [Ext.DomQuery.select('input[id=' + sflInput.tagName + '-dt-pkr]', form)[0],
                                    Ext.DomQuery.select('input[id=' + sflInput.tagName + '-tm-pkr]', form)[0]];
              }
              if (sflView && /^varWidget/i.test(sflView)) { //special case for var widget
                  var formInputs = [Ext.DomQuery.select('textarea[id=' + sflInput.tagName + '-id]', form)[0]]
              }
              if (sflView && /^textarea/i.test(sflView)) { //special case for textarea widget
                  var formInputs = [Ext.DomQuery.select('textarea[id=' + sflInput.tagName + '-id]', form)[0]]
              }
              if (sflView && /^checkbox/i.test(sflView)) { //special case for unimplemented checkbox widget
                  var formInputs = [Ext.DomQuery.select('textarea[id=' + sflInput.tagName + '-id]', form)[0]]
              }
              if (formInputs.length == 0) {
                  Ext.Msg.alert("Error:", "Unable to find matching form input for " + sflInput.tagName);
                  return false;
              }
    
              /* loop over form inputs and validate */
              for (var j=0; j < formInputs.length; j++) {
                  var formInput = formInputs[j];
    
                  /* get class to check if extjs has invalidated it */
                  var formInputClass = formInput.getAttribute('class');
                  if (formInputClass == null) continue; //skip validation if no class was set
                  if (/invalid/i.test(formInputClass)) {
                      errorsFound++;
                      errorMsg += sflInput.tagName + "<br/>"
                  }
              }
          }
    
          /* alert if errors found otherwise continue with submission */
          if (errorsFound) {
              Ext.Msg.alert("Invalid inputs:", errorMsg);
              return false;
          }else  return true;
      }catch(err) {
          Ext.Msg.alert("Error:", err);
          return false;
      }
  }
</script>
<a id="main" name="main"></a>
<form enctype="multipart/form-data" name="scifloInputForm" id="scifloInputForm" method="POST">
<h1>$scifloName</h1>
<pre>$scifloDesc</pre><br/>
<table>
<thead><h1>Sciflo Inputs</h1></thead>
<tbody>
$inputRows
</tbody>
</table>
<input type="hidden" id="scifloStr" name="scifloStr" value="$scifloStr" />
<input type="hidden" name="basicTemplate" value="$basicTemplate" />
<input id="submitCache" type="submit" name="submit" value="submitSciflo" onclick="return validateForm();" />
<input id="submitNoCache" type="submit" name="submit" value="submit w/ no cache" onclick="return validateForm();" />
</form>''')

inputRowTextTpl = Template('''
<tr><td><label for="${inputTag}-id"><b>$inputTag</b></label>:</td><td><div id="$inputTag-tb"></div>
<script type="text/javascript">
  //custom vtype for textbox validation
  var tagTest = /[<>#!&]/i;
  Ext.apply(Ext.form.VTypes, {
    clean: function(val, field) {
      if (tagTest.test(val)) return false;
      return true;
    },
    cleanText: 'Not a valid text value.  The following chars are prohibited: <>#!&'
  });
Ext.onReady(function() {
    var tb = new Ext.form.TextField({
        renderTo: '$inputTag-tb',
        id: '$inputTag-id',
        name: '$inputTag',
        value: '$inputVal',
        allowBlank: false,
        vtype: 'clean',
        autoCreate: {tag: 'input', type: 'text', size: $size},
    });
});
</script>
</td></tr>
''')

inputRowTextareaTpl = Template('''
<tr><td><label for="${inputTag}-id"><b>$inputTag</b></label>:</td><td><textarea name="$inputTag" id="$inputTag-id"
cols="$cols" rows="$rows">$inputVal</textarea>
<script type="text/javascript">
  //custom vtype for textarea validation
  var tagTest = /[<>#!&]/i;
  Ext.apply(Ext.form.VTypes, {
    clean: function(val, field) {
      if (tagTest.test(val)) return false;
      return true;
    },
    cleanText: 'Not a valid text value.  The following chars are prohibited: <>#!&'
  });
Ext.onReady(function() {
    var ta = new Ext.form.TextArea({
        applyTo: '$inputTag-id',
        id: '$inputTag-id',
        name: '$inputTag',
        allowBlank: false,
        vtype: 'clean'
    });
});
</script>
</td></tr>
''')

#view attribute matches
TEXTAREA_RE = re.compile(r'textarea\(\s*rows\s*=\s*(\d*)\s*,\s*cols\s*=\s*(\d*)\s*\)$')
TEXT_RE = re.compile(r'textbox\(\s*size\s*=\s*(\d*)\s*\)$')
COMBOBOX_RE = re.compile(r'combobox\(\s*size\s*=\s*(\d*)\s*,\s*dataUrl\s*=\s*(.*?)\s*\)$')
COMBOBOX_INLINE_RE = re.compile(r'combobox\(\s*size\s*=\s*(\d*)\s*,\s*choices\s*=\s*(.*?)\s*\)$')
VARWIDGET_RE = re.compile(r'varWidget\(\s*size\s*=\s*(\d*)\s*,\s*dataUrl\s*=\s*(.*?)\s*\)$')
DATETIME_RE = re.compile(r'datetime\(\s*(?:(start|end)\s*=\s*(.*?))?(?:,.*?)?\)')
BBOX_RE = re.compile(r'bbox\(\s*(.*?)\s*\)$')

inputFileTpl = Template('''
<tr><td><label for="${inputTag}-id"><b>$inputTag</b></label>:</td><td><input type="file" name="$inputTag" id="$inputTag-id" size="$size"/></td></tr>
''')

comboBoxInlTpl = Template('''
<tr><td><label for="${inputTag}-id"><b>$inputTag</b></label>:</td><td><div id="$inputTag-cb"></div>
<script type="text/javascript">
Ext.onReady(function() {
    varData = [$choices];
    var choices = new Array();
    for (var i=0; i < varData.length; i++) {
        choices[i] = [varData[i], varData[i]];
    }
    var cb = new Ext.form.ComboBox({
        renderTo: '$inputTag-cb',
        id: '$inputTag-id',
        name: '$inputTag',
        typeAhead: true,
        triggerAction: 'all',
        editable: false,
        mode: 'local',
        store: new Ext.data.SimpleStore({
            data: choices,
            fields: ['choice', 'val']
        }),
        displayField: 'choice',
        valueField: 'val'
    });
    cb.setValue("$inputVal");
});
</script>
</td></tr>
''')

comboBoxTpl = Template('''
<tr><td><label for="${inputTag}-id"><b>$inputTag</b></label>:</td><td><div id="$inputTag-cb"></div>
<script type="text/javascript">
Ext.onReady(function() {
    var varData = "";
    Ext.Ajax.request({
        url: 'utils.cgi',
        method: 'POST',
        success: function(r, o) {
            varData = r.responseText;
        },
        params: {func: 'getVarData4CB', dataUrl: '$dataUrl'},
        async: false
    });
    varData = eval(varData);
    var choices = new Array();
    for (var i=0; i < varData.length; i++) {
        choices[i] = [varData[i][0], varData[i][0]];
    }
    var cb = new Ext.form.ComboBox({
        renderTo: '$inputTag-cb',
        id: '$inputTag-id',
        name: '$inputTag',
        typeAhead: true,
        triggerAction: 'all',
        editable: false,
        mode: 'local',
        store: new Ext.data.SimpleStore({
            data: choices,
            fields: ['group', 'val']
        }),
        displayField: 'group',
        valueField: 'val'
    });
    cb.setValue("$inputVal");
});
</script>
</td></tr>
''')

varWidgetTpl = Template('''
<tr><td valign="top"><label for="${inputTag}-id"><b>$inputTag</b></label>:</td>
<td><label for="${inputTag}-groups-id"><font color="blue">Groups:</font></label><div id="$inputTag-group"></div>
<label for="${inputTag}-dimensions-id"><font color="blue">Dimensions:</font></label><div id="$inputTag-dimDiv"></div><hr/>
<table><tr><td><label for="${inputTag}-variables-id"><font color="blue">Variables:</font></label></td><td><div id="$inputTag-cbg-selectall"></div></td></tr></table>
<div id="$inputTag-cbgDiv"></div>
<div id="$inputTag-tbDiv"></div>
<script type="text/javascript">
Ext.onReady(function() {
    var varData = "";
    Ext.Ajax.request({
        url: 'utils.cgi',
        method: 'POST',
        success: function(r, o) {
            varData = r.responseText;
        },
        params: {func: 'getVarData4CB', dataUrl: '$dataUrl'},
        async: false
    });
    varData = eval(varData);
    var choices = new Array();
    for (var i=0; i < varData.length; i++) {
        choices[i] = [varData[i][0], varData[i][0]];
    }
    var cb = new Ext.form.ComboBox({
        renderTo: '$inputTag-group',
        name: '$inputTag-group-cb',
        typeAhead: true,
        triggerAction: 'all',
        editable: false,
        mode: 'local',
        store: new Ext.data.SimpleStore({
            data: choices,
            fields: ['group', 'val']
        }),
        displayField: 'group',
        valueField: 'val'
    });
    cb.on('select', function(c, r, i) {
        //dim description text
        var edim = Ext.getCmp('$inputTag-dimDiv-html');
        if (edim) {
            edim.hide();
            edim.destroy();
        }
        var edimItems = new Array();
        for (d in varData[i][1]) {
            /* function to update tb */
            var updateTb = function() {
                var cbItems = Ext.getCmp('$inputTag-cbgDiv-cbg').items;
                var tbVars = new Array();
                for (var cbCount=0; cbCount < cbItems.length; cbCount++) {
                    var cbItem = cbItems.items[cbCount];
                    var lbl = cbItem.boxLabel.replace(/\s*\[.*?\]/g, "");
                    if (cbItem.checked) {
                        var tbdimVars = new Array();
                        for (var dimidx=0; dimidx < varData[i][3][lbl].length; dimidx++) {
                            var vardim = varData[i][3][lbl][dimidx];
                            if (varData[i][1][vardim][0] == 'false') {
                                var globalSlice = Ext.getCmp('$inputTag-dim-' + vardim);
                                if (globalSlice.getValue() != '[]' && globalSlice.getValue() != '') {
                                    tbdimVars.push(globalSlice.getValue());
                                }
                            }
                        }
                        if (tbdimVars.length > 0) tbVars.push("'" + lbl + tbdimVars.join("") + "'");
                        else tbVars.push("'" + lbl + "'");
                    }
                }
                var tbVarStr = "[ " + tbVars.join(", ") + " ]";
                Ext.getCmp('$inputTag-id').setValue(varData[i][0] + "/" + tbVarStr);
            };

            if (varData[i][1][d][0] == 'false') {
                edimItems.push({
                    xtype: 'textfield',
                    id: '$inputTag-dim-' + d,
                    width: 80,
                    //grow: true,
                    fieldLabel: d,
                    enableKeyEvents: true,
                    value: '[' + varData[i][1][d][1] + ']',
                    listeners: {
                        'keypress': function(t, e) {
                            setTimeout(updateTb, 10);
                        }
                    }
                });
                //edimItems.push(d + " = " + varData[i][1][d][1] + \
                //    ' <input id="$inputTag-dim-' + d + \
                //    '" type="text" size="3" value="[]" class="x-form-text x-form-field"' + \
                //    ' onkeypress="alert(\\'Hello\\');"/>');
            }
        }
        var dims = new Ext.Container({
            layout: 'form',
            renderTo: '$inputTag-dimDiv',
            id: '$inputTag-dimDiv-html',
            autoEl: {},
            items: edimItems
            //autoEl: {html: edimItems.join(", ")}
        });
        
        //custom vtype for textarea validation
        var tagTest = /[<>#!&]/i;
        Ext.apply(Ext.form.VTypes, {
            clean: function(val, field) {
                if (tagTest.test(val)) return false;
                return true;
            },
            cleanText: 'Not a valid text value.  The following chars are prohibited: <>#!&'
        });
 
        //textbox
        var etbc = Ext.getCmp('$inputTag-id');
        if (etbc) {
            etbc.hide();
            etbc.destroy();
        }
        var tbc = new Ext.form.TextArea({
            renderTo: '$inputTag-tbDiv',
            id: '$inputTag-id',
            name: '$inputTag',
            width: 600,
            value: '$inputVal',
            grow: true,
            allowBlank: false,
            vtype: 'clean'
        });
        
        //checkbox group
        var ecbg = Ext.getCmp('$inputTag-cbgDiv-cbg');
        if (ecbg) {
            ecbg.hide();
            ecbg.destroy();
        }
        var items = new Array();
        for (v in varData[i][3]) {
            var varName = v;
            var varDimList = new Array();
            for (var dimidx=0; dimidx < varData[i][3][v].length; dimidx++) {
                var vardim = varData[i][3][v][dimidx];
                if (varData[i][1][vardim][0] == 'false') {
                    varDimList.push(vardim.replace(/^N(.*)Dim$$/, "$$1"));
                }
            }
            if (varDimList.length > 0) varName += ' [' + varDimList.join(', ') + ']';
            items.push({
                boxLabel: varName,
                name: '__VARDATA__' + varData[i][0] + '__' + varName,
                listeners: {
                    'check': updateTb
                }
            });
        }
        var cbg = new Ext.form.CheckboxGroup({
            renderTo: '$inputTag-cbgDiv',
            id: '$inputTag-cbgDiv-cbg',
            columns: [600],
            items: items
        });
        var etbc = Ext.getCmp('$inputTag-cbg-selectall-select');
        if (etbc) {
            etbc.hide();
            etbc.destroy();
        }
        var cbgSelectAll = new Ext.form.Checkbox({
            boxLabel: 'select all',
            renderTo: '$inputTag-cbg-selectall',
            id: '$inputTag-cbg-selectall-select',
            columns: [600],
            listeners: {
                'check': {
                    fn: function(cb, checkVal) {
                        var cbItems = Ext.getCmp('$inputTag-cbgDiv-cbg').items;
                        for (var cbCount=0; cbCount < cbItems.length; cbCount++) {
                            var cbItem = cbItems.items[cbCount];
                            cbItem.setValue(checkVal);
                        }
                    }
                }
            }
        });
    });
    cb.setValue('$inputValCb');
    var cbRecordIdx = cb.store.find('val', '$inputValCb');
    var cbRecord = cb.store.getAt(cbRecordIdx);
    cb.fireEvent('select', cb, cb.store.getAt(cbRecordIdx), cbRecordIdx);
});
</script>
</td></tr>
''')

datetimePickerTpl = Template('''
<tr><td><label for="${inputTag}-id"><b>$inputTag</b></label>:</td>
<td>
<table><tr><td><div id="$inputTag-dt"></div></td>
<td><div id="$inputTag-tm"></div></td>
<td><div id="$inputTag-tbDiv"></div></tr></table>
<script type="text/javascript">
Ext.onReady(function() {
    var tbc = new Ext.form.TextField({
            renderTo: '$inputTag-tbDiv',
            id: '$inputTag-id',
            name: '$inputTag',
            value: '$inputVal',
            hidden: true
    });
    var setTbc = function() {
        var thisdt = Ext.getCmp('$inputTag-dt-pkr');
        var thistm = Ext.getCmp('$inputTag-tm-pkr');
        var thistbc = Ext.getCmp('$inputTag-id');
        thistbc.setValue(thisdt.getValue().format('Y-m-d') + ' ' + thistm.getValue());
    };
    var setTbcIfEnter = function(t, e) {
       if (e.getKey() == 13) setTbc();
    }; 
    var dt = new Ext.form.DateField({
        renderTo: '$inputTag-dt',
        id: '$inputTag-dt-pkr',
        format: 'Y-m-d',
        value: '$inputValDt',
        listeners: {'select': setTbc,
                    'change': setTbc,
                    'specialkey': setTbcIfEnter
        }
    });
    var tm = new Ext.form.TimeField({
        renderTo: '$inputTag-tm',
        id: '$inputTag-tm-pkr',
        format: 'H:i:s',
        minValue: '00:00:00',
        maxValue: '23:59:59',
        value: '$inputValTm',
        listeners: {'select': setTbc,
                    'change': setTbc,
                    'specialkey': setTbcIfEnter
        }
    });
});
</script>
</td></tr>
''')

datetimePickerStartTpl = Template('''
<tr><td><label for="${inputTag}-id"><b>$inputTag</b></label>:</td>
<td>
<table><tr><td><div id="$inputTag-dt"></div></td>
<td><div id="$inputTag-tm"></div></td>
<td><div id="$inputTag-tbDiv"></div></tr></table>
<script type="text/javascript">
Ext.onReady(function() {
    var tbc = new Ext.form.TextField({
            renderTo: '$inputTag-tbDiv',
            id: '$inputTag-id',
            name: '$inputTag',
            value: '$inputVal',
            hidden: true
    });
    var setTbc = function() {
        var thisdt = Ext.getCmp('$inputTag-dt-pkr');
        var thistm = Ext.getCmp('$inputTag-tm-pkr');
        var thistbc = Ext.getCmp('$inputTag-id');
        thistbc.setValue(thisdt.getValue().format('Y-m-d') + ' ' + thistm.getValue());
        var matchdt = Ext.getCmp('$matchingTag-dt-pkr');
        var matchdate = matchdt.getValue();
        var thisdate = thisdt.getValue();
        matchdt.setMinValue(thisdate);
        matchdt.validate();
        thisdt.dateRangeMax = matchdate;
        thisdt.validate();
        var matchtm = Ext.getCmp('$matchingTag-tm-pkr');
        if (thisdate.format('Y-m-d') == matchdate.format('Y-m-d')) {
            /* filter this timefield's range */
            thistm.store.clearFilter();
            thistm.store.filterBy(function(rec, recid) {
                if (thistm.parseDate(rec.data.text) < thistm.parseDate(matchtm.getValue())) return true;
                else return false;
            });
            
            /* filter matching timefield's range */
            matchtm.store.clearFilter();
            matchtm.store.filterBy(function(rec, recid) {
                if (matchtm.parseDate(rec.data.text) > matchtm.parseDate(thistm.getValue())) return true;
                else return false;
            });
        }else {
            thistm.store.clearFilter();
            matchtm.store.clearFilter();
        }
    };
    var setTbcIfEnter = function(t, e) {
       if (e.getKey() == 13) setTbc();
    }; 
    var dt = new Ext.form.DateField({
        renderTo: '$inputTag-dt',
        id: '$inputTag-dt-pkr',
        format: 'Y-m-d',
        value: '$inputValDt',
        listeners: {'select': setTbc,
                    'change': setTbc,
                    'specialkey': setTbcIfEnter
        }
    });
    var tm = new Ext.form.TimeField({
        renderTo: '$inputTag-tm',
        id: '$inputTag-tm-pkr',
        format: 'H:i:s',
        minValue: '00:00:00',
        maxValue: '23:59:59',
        value: '$inputValTm',
        listeners: {'select': setTbc,
                    'change': setTbc,
                    'specialkey': setTbcIfEnter
        }
    });
});
</script>
</td></tr>
''')

datetimePickerEndTpl = Template('''
<tr><td><label for="${inputTag}-id"><b>$inputTag</b></label>:</td>
<td>
<table><tr><td><div id="$inputTag-dt"></div></td>
<td><div id="$inputTag-tm"></div></td>
<td><div id="$inputTag-tbDiv"></div></tr></table>
<script type="text/javascript">
Ext.onReady(function() {
    var tbc = new Ext.form.TextField({
            renderTo: '$inputTag-tbDiv',
            id: '$inputTag-id',
            name: '$inputTag',
            value: '$inputVal',
            hidden: true
    });
    var setTbc = function() {
        var thisdt = Ext.getCmp('$inputTag-dt-pkr');
        var thistm = Ext.getCmp('$inputTag-tm-pkr');
        var thistbc = Ext.getCmp('$inputTag-id');
        thistbc.setValue(thisdt.getValue().format('Y-m-d') + ' ' + thistm.getValue());
        var date = thisdt.getValue();
        var matchdt = Ext.getCmp('$matchingTag-dt-pkr');
        var matchdate = matchdt.getValue();
        var thisdate = thisdt.getValue();
        matchdt.setMaxValue(thisdate);
        matchdt.validate();
        thisdt.dateRangeMin = matchdate;
        thisdt.validate();
        var matchtm = Ext.getCmp('$matchingTag-tm-pkr');
        if (thisdate.format('Y-m-d') == matchdate.format('Y-m-d')) {
            /* filter this timefield's range */
            thistm.store.clearFilter();
            thistm.store.filterBy(function(rec, recid) {
                if (thistm.parseDate(rec.data.text) > thistm.parseDate(matchtm.getValue())) return true;
                else return false;
            });
            
            /* filter matching timefield's range */
            matchtm.store.clearFilter();
            matchtm.store.filterBy(function(rec, recid) {
                if (matchtm.parseDate(rec.data.text) < matchtm.parseDate(thistm.getValue())) return true;
                else return false;
            });
        }else {
            thistm.store.clearFilter();
            matchtm.store.clearFilter();
        }
    };
    var setTbcIfEnter = function(t, e) {
       if (e.getKey() == 13) setTbc();
    }; 
    var dt = new Ext.form.DateField({
        renderTo: '$inputTag-dt',
        id: '$inputTag-dt-pkr',
        format: 'Y-m-d',
        value: '$inputValDt',
        listeners: {'select': setTbc,
                    'change': setTbc,
                    'specialkey': setTbcIfEnter
        }
    });
    var tm = new Ext.form.TimeField({
        renderTo: '$inputTag-tm',
        id: '$inputTag-tm-pkr',
        format: 'H:i:s',
        minValue: '00:00:00',
        maxValue: '23:59:59',
        value: '$inputValTm',
        listeners: {'select': setTbc,
                    'change': setTbc,
                    'specialkey': setTbcIfEnter
        }
    });
    Ext.getCmp('$matchingTag-dt-pkr').fireEvent('select');
    setTbc();
});
</script>
</td></tr>
''')

GMAP_KEY = sciflo.utils.ScifloConfigParser().getParameter('gmapKey')
bboxTpl = Template('''
<tr><td valign="top">
<table>
<tr><td height="25"><label for="${lat_min}-id"><b>$lat_min</b></label>:</td></tr>
<tr><td height="25"><label for="${lat_max}-id"><b>$lat_max</b></label>:</td></tr>
<tr><td height="25"><label for="${lon_min}-id"><b>$lon_min</b></label>:</td></tr>
<tr><td height="25"><label for="${lon_max}-id"><b>$lon_max</b></label>:</td></tr></table>
</td>
<td>
<table><tr>
<td valign="top"><table>
<tr>
  <td height="25"><div id="$lat_min-tbDiv"/></td>
</tr>
<tr>
  <td height="25"><div id="$lat_max-tbDiv"/></td>
</tr>
<tr>
  <td height="25"><div id="$lon_min-tbDiv"/></td>
</tr>
<tr>
  <td height="25"><div id="$lon_max-tbDiv"/></td>
</tr>
<tr>
  <td height="25"><div id="cb-round"></div></td>
</tr></table>
</td><td><div id="map_canvas" style="width: 450px; height: 300px; border-style:solid"></div>
<center><i>(click once to place a marker, then drag the marker to select a region)</i></center>
<script src="http://maps.google.com/maps?file=api&amp;v=2&amp;key=$gmapKey&sensor=false"
  type="text/javascript"></script>
  <script type="text/javascript">
  //put ur start and end variables here
  var startPoint;
  var endPoint;
  var area;
  var lastRect;
  var dragEnd;
  
  function roundAccuracy(num, acc) {
    //var factor = Math.pow(10, acc);
    //return Math.round(num/factor)*factor;
    return Math.round(num);
  }

  //custom vtypes for lat/lon validation
  var latTest = /^-?[0-9]{0,2}(?:\.[0-9]*)?$$/i;
  var lonTest = /^-?[0-9]{0,3}(?:\.[0-9]*)?$$/i;
  Ext.apply(Ext.form.VTypes, {
    lat: function(val, field) {
      var ret = latTest.test(val);
      if (ret) {
        var lat = parseFloat(val);
        if (lat < -90 || lat > 90) return false;
        else return true;
      }
      return ret;
    },
    latText: 'Not a valid latitude value.  Must be -90. <= lat <= 90.',
    latMask: /[\d-\.]/i
  });
  Ext.apply(Ext.form.VTypes, {
    lon: function(val, field) {
      var ret = lonTest.test(val);
      if (ret) {
        var lon = parseFloat(val);
        if (lon < -180 || lon > 180) return false;
        else return true;
      }
      return ret;
    },
    lonText: 'Not a valid longitude value.  Must be -180. <= lon <= 180.',
    lonMask: /[\d-\.]/i
  });

  function initialize() {
  
    var latMinTb = new Ext.form.TextField({
            renderTo: '$lat_min-tbDiv',
            id: '$lat_min',
            name: '$lat_min',
            value: '$lat_min_value',
            allowBlank: false,
            vtype: 'lat'
    });
    var latMaxTb = new Ext.form.TextField({
            renderTo: '$lat_max-tbDiv',
            id: '$lat_max',
            name: '$lat_max',
            value: '$lat_max_value',
            allowBlank: false,
            vtype: 'lat'
    });
    var lonMinTb = new Ext.form.TextField({
            renderTo: '$lon_min-tbDiv',
            id: '$lon_min',
            name: '$lon_min',
            value: '$lon_min_value',
            allowBlank: false,
            vtype: 'lon'
    });
    var lonMaxTb = new Ext.form.TextField({
            renderTo: '$lon_max-tbDiv',
            id: '$lon_max',
            name: '$lon_max',
            value: '$lon_max_value',
            allowBlank: false,
            vtype: 'lon'
    });

    // check box for rounding
    var cbRound = new Ext.form.Checkbox({
      boxLabel: 'round?',
      renderTo: 'cb-round',
      id: 'cb-round-select',
      checked: true,
      columns: [600]
    });
        
    if (GBrowserIsCompatible()) {
      var map = new GMap2(document.getElementById("map_canvas"));
      map.setCenter(new GLatLng(1, 1), 1); //this shows world map
     
      map.setMapType(G_HYBRID_MAP);
      map.disableDragging();
      map.disableScrollWheelZoom();
      map.addControl(new GLargeMapControl());
      map.addControl(new GMapTypeControl());
      startPoint = 0;
      endPoint = 0;
      GEvent.addListener(map,"click", function(overlay,latlng) {
        if (overlay || dragEnd) {
          // ignore if we click on the info window
          dragEnd = false;
          return;
        }

        map.clearOverlays();    
        var marker = new GMarker(latlng, {draggable: true});
        GEvent.addListener(marker, "dragstart", function() {
          //capture initial coord
          dragEnd = false;
          startPoint = marker.getLatLng();
        });
        function drawRect(marker) {
          if (marker) {
            //capture new coord and generate new rectangle
            endPoint = marker.getLatLng();
          
            //rounding is checked
            var cbRound = Ext.getCmp('cb-round-select');
      
            //create 2 new glatlongs for southwest and northeast and
            //with this create a GLatLongBound and a new rectangle
            //min lat,min lng = SW
            //max lat, max lat = NE
            if(startPoint.lat() > endPoint.lat()){
              var swLat = endPoint.lat(); //min
              var neLat = startPoint.lat();//max
              if(cbRound.getValue()) {
                document.getElementById("$lat_max").value=roundAccuracy(neLat, -1);
                document.getElementById("$lat_min").value=roundAccuracy(swLat, -1);
              }else {
                document.getElementById("$lat_max").value=neLat;
                document.getElementById("$lat_min").value=swLat;
              }
            }else{
              var swLat = startPoint.lat();
              var neLat = endPoint.lat();
              if(cbRound.getValue()) {
                document.getElementById("$lat_max").value=roundAccuracy(neLat, -1);
                document.getElementById("$lat_min").value=roundAccuracy(swLat, -1);
              }else {
                document.getElementById("$lat_max").value=neLat;
                document.getElementById("$lat_min").value=swLat;
              }
            }
          
            if(startPoint.lng() > endPoint.lng()){
              var swLng = endPoint.lng();
              var neLng = startPoint.lng();
              if(cbRound.getValue()) {
                document.getElementById("$lon_max").value=roundAccuracy(neLng, -1);
                document.getElementById("$lon_min").value=roundAccuracy(swLng, -1);
              }else {
                document.getElementById("$lon_max").value=neLng;
                document.getElementById("$lon_min").value=swLng;
              }
            }else{
              var swLng = startPoint.lng();
              var neLng = endPoint.lng();
              if(cbRound.getValue()) {
                document.getElementById("$lon_max").value=roundAccuracy(neLng, -1);
                document.getElementById("$lon_min").value=roundAccuracy(swLng, -1);
              }else {
                document.getElementById("$lon_max").value=neLng;
                document.getElementById("$lon_min").value=swLng;
              }
            }
          }else {
            var latmin = parseFloat(document.getElementById("$lat_min").value);
            var latmax = parseFloat(document.getElementById("$lat_max").value);
            var lonmin = parseFloat(document.getElementById("$lon_min").value);
            var lonmax = parseFloat(document.getElementById("$lon_max").value);
            if (latmin > latmax) {
              var swLat = latmax;
              var neLat = latmin;
              document.getElementById("$lat_min").value = latmax;
              document.getElementById("$lat_max").value = latmin;
            }else {
              var swLat = latmin;
              var neLat = latmax;
            }
            if (lonmin > lonmax) {
              var swLng = lonmax;
              var neLng = lonmin;
              document.getElementById("$lon_min").value = lonmax;
              document.getElementById("$lon_max").value = lonmin;
            }else {
              var swLng = lonmin;
              var neLng = lonmax;
            }
          }

          //validate all
          latMinTb.validate();
          latMaxTb.validate();
          lonMinTb.validate();
          lonMaxTb.validate();

          //console.log(swLat, swLng, neLat, neLng);
          var rectBounds = new GLatLngBounds(
            new GLatLng(swLat, swLng),
            new GLatLng(neLat, neLng)
          );
          if(lastRect) map.removeOverlay(lastRect);
          lastRect = new Rectangle(rectBounds);
          map.addOverlay(lastRect);
        };
        GEvent.addListener(marker, "drag", function() {drawRect(marker);});
        GEvent.addListener(marker, "dragend", function() {
            dragEnd = true;
            drawRect(marker)});
        map.addOverlay(marker);

        /*add listeners for change of values in textbox */
        latMinTb.addListener('change', function() {
          dragEnd = true;
          drawRect();
        });
        latMaxTb.addListener('change', function() {
          dragEnd = true;
          drawRect();
        });
        lonMinTb.addListener('change', function() {
          dragEnd = true;
          drawRect();
        });
        lonMaxTb.addListener('change', function() {
          dragEnd = true;
          drawRect();
        });
      });

      /* add default rect, marker, and help window */
      var latlng = new GLatLng($lat_max_value, $lon_max_value);
      if (($lat_max_value == 90) || ($lat_min_value == -90)) {
        var latlng = new GLatLng(-45, -30);
      }
      GEvent.trigger(map, "click", false, latlng);
      //map.openInfoWindowHtml(latlng, "Drag marker to draw bounding box.");
      var rectBounds = new GLatLngBounds(
        new GLatLng($lat_min_value, $lon_min_value),
        new GLatLng($lat_max_value, $lon_max_value)
      );
      if(lastRect) map.removeOverlay(lastRect);
      lastRect = new Rectangle(rectBounds);
      map.addOverlay(lastRect);
    }
  }
  Ext.onReady(initialize);

  // A Rectangle is a simple overlay that outlines a lat/lng bounds on the
  // map. It has a border of the given weight and color and can optionally
  // have a semi-transparent background color.
  function Rectangle(bounds, opt_weight, opt_color) {
    this.bounds_ = bounds;
    this.weight_ = opt_weight || 2;
    this.color_ = opt_color || "yellow";
  }

  Rectangle.prototype = new GOverlay();

  // Creates the DIV representing this rectangle.
  Rectangle.prototype.initialize = function(map) {
    // Create the DIV representing our rectangle
    var div = document.createElement("div");
    div.style.border = this.weight_ + "px solid " + this.color_;
    div.style.position = "absolute";

    // Our rectangle is flat against the map, so we add our selves to the
    // MAP_PANE pane, which is at the same z-index as the map itself (i.e.,
    // below the marker shadows)
    map.getPane(G_MAP_MAP_PANE).appendChild(div);
    this.map_ = map;
    this.div_ = div;
  }

  // Remove the main DIV from the map pane
  Rectangle.prototype.remove = function() {
    this.div_.parentNode.removeChild(this.div_);
  }

  // Copy our data to a new Rectangle
  Rectangle.prototype.copy = function() {
    return new Rectangle(this.bounds_, this.weight_, this.color_,
      this.backgroundColor_, this.opacity_);
  }

  // Redraw the rectangle based on the current projection and zoom level
  Rectangle.prototype.redraw = function(force) {
    // We only need to redraw if the coordinate system has changed
    if (!force) return;

    // Calculate the DIV coordinates of two opposite corners of our bounds to
    // get the size and position of our rectangle
    var c1 = this.map_.fromLatLngToDivPixel(this.bounds_.getSouthWest());
    var c2 = this.map_.fromLatLngToDivPixel(this.bounds_.getNorthEast());

    // Now position our DIV based on the DIV coordinates of our bounds
    this.div_.style.width = Math.abs(c2.x - c1.x) + "px";
    this.div_.style.height = Math.abs(c2.y - c1.y) + "px";
    this.div_.style.left = (Math.min(c2.x, c1.x) - this.weight_) + "px";
    this.div_.style.top = (Math.min(c2.y, c1.y) - this.weight_) + "px";
  }
</script>
</td></tr></table>
</td></tr>
''')

def printForm():
    """Just print the form."""

    #print header
    print "Content-Type: text/html\n\n"

    #print html
    print pageTemplate.pageTemplateHead.substitute(title='Upload SciFlo',
                                                   additionalHead='',
                                                   bodyOnload='')

    print uploadScifloTpl.substitute({'spaces':spacesStr})

    #print end
    print pageTemplate.pageTemplateFoot.substitute()

def printInputForm(scifloStr, form):
    """Input form."""

    #get reset
    reset = form.getfirst('reset',False)
    if isinstance(reset, types.StringTypes): reset = sanitizeHtml(reset)

    #get template
    basicTemplate = form.getfirst('basicTemplate',None)
    if basicTemplate is None or (isinstance(basicTemplate, types.StringTypes) and \
    re.search(r'false', basicTemplate, re.IGNORECASE)): basicTemplate = 'FALSE'
    else: basicTemplate = 'TRUE'

    #check if valid sciflo doc
    sfl = sciflo.grid.doc.Sciflo(urllib2.urlopen(scifloStr).read())
    sfl.resolve()
    
    #bbox set
    bboxElts = []
    
    #get interface config
    interfaceCfg = cjson.decode(getTabConfig(scifloStr))
    sectionCfgs = [interfaceCfg['setupTab']]
    sectionCfgs.extend(interfaceCfg['tabs'])

    #generate input dictionary from forms
    inputRows = []
    for sectionCfg in sectionCfgs:
        inputRows.append('<tr><td><font size="3" color="blue">%s</font></td><td></td></tr>' % sectionCfg['title'])
        inputRows.append('<tr><td><hr/></td><td><hr/></td></tr>')
        for item in sectionCfg['items']:
            if item.has_key('sflGlobalInput'): inputTags = [item['sflGlobalInput']]
            else:
                inputRows.append('<tr><td><font size="2" color="blue">%s</font></td><td></td></tr>' % item['title'])
                inputTags = [subitem['sflGlobalInput'] for subitem in item['items']]
            
            for inputTag in inputTags:
                for inputElt in sfl._flowInputs:
                    if inputTag != inputElt.tag: continue
                    
                    #file upload?
                    inputType = inputElt.get('type')
                    if inputType is not None and inputType == 'sf:fileUpload':
                        inputRows.append(inputFileTpl.substitute({'inputTag': inputTag,
                                                                  'size': '100'}))
                        break
            
                    #view
                    view = inputElt.get('view')
                    if view is not None:
                        typ, viewDict = parseView(view)
                        
                        #text widget
                        textMatch = TEXT_RE.search(view)
                        if textMatch:
                            inputRows.append(inputRowTextTpl.substitute({'inputTag': inputTag,
                                                                         'inputVal': inputElt.text,
                                                                         'size': str(viewDict['size'])}))
                            break
                        
                        #textarea widget
                        textareaMatch = TEXTAREA_RE.search(view)
                        if textareaMatch:
                            inputRows.append(inputRowTextareaTpl.substitute({'inputTag': inputTag,
                                                                             'inputVal': inputElt.text,
                                                                             'rows': str(viewDict['rows']),
                                                                             'cols': str(viewDict['cols'])}))
                            break
                        
                        #combobox widget
                        comboBoxMatch = COMBOBOX_RE.search(view)
                        if comboBoxMatch:
                            inputRows.append(comboBoxTpl.substitute({'inputTag': inputTag,
                                                                     'inputVal': inputElt.text,
                                                                     'size': str(viewDict['size']),
                                                                     'dataUrl': str(viewDict['dataUrl'])}))
                            break
                        
                        #inline combobox widget
                        comboBoxMatch = COMBOBOX_INLINE_RE.search(view)
                        if comboBoxMatch:
                            inputRows.append(comboBoxInlTpl.substitute({'inputTag': inputTag,
                                                                        'inputVal': inputElt.text,
                                                                        'size': str(viewDict['size']),
                                                                        'choices': str(viewDict['choices'])}))
                            break
                        
                        #varWidget widget
                        varWidgetMatch = VARWIDGET_RE.search(view)
                        if varWidgetMatch:
                            inputRows.append(varWidgetTpl.substitute({'inputTag': inputTag,
                                                                     'inputVal': inputElt.text.replace("'", "\\'"),
                                                                     'inputValCb': inputElt.text.split('/')[0],
                                                                     'size': str(viewDict['size']),
                                                                     'dataUrl': str(viewDict['dataUrl'])}))
                            break
                        
                        #datetime widget
                        datetimeMatch = DATETIME_RE.search(view)
                        if datetimeMatch:
                            timeElms = sciflo.utils.getTimeElementsFromString(inputElt.text)
                            matchingDtType, matchingDtTag = datetimeMatch.groups()
                            if matchingDtType is None:
                                inputRows.append(datetimePickerTpl.substitute({'inputTag': inputTag,
                                                                               'inputVal': inputElt.text,
                                                                               'inputValDt': '%04d-%02d-%02d' % \
                                                                                   (timeElms[0], timeElms[1],
                                                                                    timeElms[2]),
                                                                               'inputValTm': '%02d:%02d:%02d' % \
                                                                                   (timeElms[3], timeElms[4],
                                                                                    timeElms[5])
                                                                               }))
                            else:
                                if matchingDtType == 'start':
                                    inputRows.append(datetimePickerEndTpl.substitute({'inputTag': inputTag,
                                                                                   'inputVal': inputElt.text,
                                                                                   'inputValDt': '%04d-%02d-%02d' % \
                                                                                       (timeElms[0], timeElms[1],
                                                                                        timeElms[2]),
                                                                                   'inputValTm': '%02d:%02d:%02d' % \
                                                                                       (timeElms[3], timeElms[4],
                                                                                        timeElms[5]),
                                                                                   'matchingTag': matchingDtTag
                                                                                   }))
                                else:
                                    inputRows.append(datetimePickerStartTpl.substitute({'inputTag': inputTag,
                                                                               'inputVal': inputElt.text,
                                                                               'inputValDt': '%04d-%02d-%02d' % \
                                                                                   (timeElms[0], timeElms[1],
                                                                                    timeElms[2]),
                                                                               'inputValTm': '%02d:%02d:%02d' % \
                                                                                   (timeElms[3], timeElms[4],
                                                                                    timeElms[5]),
                                                                               'matchingTag': matchingDtTag
                                                                               }))
                            break
                        
                        #bbox widget
                        bboxMatch = BBOX_RE.search(view)
                        if bboxMatch:
                            bboxElts.append(inputElt)
                            if len(bboxElts) == 4:
                                convDict = {
                                    'min_lat': 'lat_min',
                                    'max_lat': 'lat_max',
                                    'min_lon': 'lon_min',
                                    'max_lon': 'lon_max'
                                }
                                bDict = {}
                                for bElt in bboxElts:
                                    bTag = bElt.tag
                                    bView = bElt.get('view')
                                    bViewType, bViewDict = parseView(bView)
                                    bMatch = BBOX_RE.search(bView)
                                    if not bboxMatch: raise RuntimeError("Couldn't find view for bbox in %s." % bView)
                                    
                                    bDict[convDict[bViewDict['cmp']]] = bTag
                                    bDict[convDict[bViewDict['cmp']] + '_value'] = bElt.text
                                bDict['size'] = '15'
                                bDict['gmapKey'] = GMAP_KEY
                                inputRows.append(bboxTpl.substitute(bDict))
                            break
                        
                    if inputElt.text is None:
                        inputText = ""
                        inputLen = 5
                    else:
                        inputText = inputElt.text
                        inputLen = len(inputText)
                    if '\n' in inputText:
                        inputRows.append(inputRowTextareaTpl.substitute({'inputTag': inputTag,
                                                                             'inputVal': inputText.replace("'", '"'),
                                                                             'rows': str(5),
                                                                             'cols': str(80)}))
                    else:
                        inputRows.append(inputRowTextTpl.substitute({'inputTag': inputTag,
                                                                     'inputVal': inputText.replace("'", '"'),
                                                                     'size': str(inputLen+1)}))
        inputRows.append('<tr><td></td><td></td></tr>')
        
    #print header
    print "Content-Type: text/html\n\n"

    #print html
    print pageTemplate.pageTemplateHead.substitute(title='Submit SciFlo',
                                                   additionalHead='',
                                                   bodyOnload='')

    print inputFormTpl.substitute({'scifloStr':scifloStr,
                                   'basicTemplate': basicTemplate,
                                   'inputRows':'\n'.join(inputRows),
                                   'scifloName': sfl._flowName,
                                   'scifloDesc': sfl._description})

    #print end
    print pageTemplate.pageTemplateFoot.substitute()

def printTest(form,extra=[]):

    #print header
    print "Content-Type: text/html\n\n"

    #print html
    print pageTemplate.pageTemplateHead.substitute(title='Submit SciFlo',
                                                   additionalHead='',
                                                   bodyOnload='')
    for i in extra: print "%s<br/>" % str(i)
    cgi.print_form(form)
    cgi.print_environ()

    #print end
    print pageTemplate.pageTemplateFoot.substitute()

def handleRequest(sfl, form, redirectToStatusPage=False, reset=False, basicTemplate=False):
    """Handle request."""

    #check if valid sciflo doc
    if sciflo.utils.isXml(sfl): sflStr = sfl
    else: sflStr = urllib2.urlopen(sfl).read()
    sfl = sciflo.grid.doc.Sciflo(sflStr)
    sfl.resolve()

    #generate input dictionary from forms
    wuArgs = []
    inputDict = {}
    for inputElt in sfl._flowInputs:
        inputTag = inputElt.tag
        if inputTag is None: continue
        formVal = form.getfirst(inputTag, None)
        if formVal is not None:
            #file upload?  Then write to a file
            inputType = inputElt.get('type')
            if inputType is not None and inputType == 'sf:fileUpload':
                tempDir = mkdtemp(); os.chmod(tempDir, 0755)
                localFile = os.path.join(tempDir, form[inputTag].filename)
                f = open(localFile, 'wb'); f.write(formVal); f.close()
                formVal = localFile
            
            inputDict[inputTag] = formVal
    if len(inputDict) > 0: wuArgs = [inputDict]

    if reset: noLookCache = True
    else: noLookCache = False
    
    #submit
    gsc = sciflo.grid.GridServiceConfig()
    gridBaseUrl = gsc.getGridProxyUrl()
    if not gridBaseUrl: gridBaseUrl = gsc.getGridBaseUrl()
    wsdl = '%s/wsdl?http://sciflo.jpl.nasa.gov/2006v1/sf/GridService' % gridBaseUrl
    #lookup cache?
    if reset: submitFuncName = 'submitSciflo_nocache'
    else: submitFuncName = 'submitSciflo'
    try:
        scifloid, jsonFile = \
            sciflo.grid.soapFuncs.submitSciflo_client(wsdl, submitFuncName, sflStr, wuArgs)
    except Exception, e:
        print "Content-Type: text/html\n\n"
        print '<font color="red">SciFlo Execution server is down.  Unable to execute sciflo.</font>'
        return

    #if redirect to status page, do so else print xml
    if redirectToStatusPage:
        if basicTemplate: print "Location: monitor_sciflo.cgi?json=%s&basicTemplate=TRUE\n\n" % jsonFile
        else: print "Location: monitor_sciflo.cgi?json=%s\n\n" % jsonFile
    else:
        print "Content-Type: text/xml\n\n"
        print '<scifloid>%s</scifloid>' % scifloid

if __name__ == '__main__':

    #get form
    form = cgi.FieldStorage()
    reset = form.getfirst('reset',False)
    if isinstance(reset, types.StringTypes): reset = sanitizeHtml(reset)
    basicTemplate = form.getfirst('basicTemplate',None)
    if basicTemplate is None or (isinstance(basicTemplate, types.StringTypes) and \
    re.search(r'false', basicTemplate, re.IGNORECASE)):
        basicTemplate = False
        import pageTemplate
    else: 
        basicTemplate = True
        import basicPageTemplate as pageTemplate
    scifloStr = form.getfirst('scifloStr',None)
    submit = form.getfirst('submit',None)
    if submit == 'submit w/ no cache': reset = 'hard'
    meth = os.environ.get('REQUEST_METHOD',None)
    if os.environ.get('SSL_PROTOCOL',None) is not None: proto = 'https'
    else: proto = 'http'
    serverName = os.environ['SERVER_NAME']

    #handle post
    if scifloStr is None: printForm()
    else:
        if scifloStr.startswith('/'): scifloStr = '%s://%s/' % (proto,serverName) + scifloStr
        elif sciflo.utils.isUrl(scifloStr) or sciflo.utils.isXml: pass
        else: raise RuntimeError, "Unknown scifloStr: %s" % scifloStr
        if submit == 'submitSciflo' or submit == 'submit w/ no cache' or sciflo.utils.isXml(scifloStr):
            handleRequest(scifloStr, form, True, reset, basicTemplate)
        elif submit is None: printInputForm(scifloStr, form)
        else: raise RuntimeError, "Unknown submit: %s" % submit
