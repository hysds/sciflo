<?xml version="1.0"?>
<xsl:transform version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:sf="http://sciflo.jpl.nasa.gov/2006v1/sf"
                xmlns:xs ="http://www.w3.org/2001/XMLSchema"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns="http://sciflo.jpl.nasa.gov/2006v1/sf"
                xmlns:str="http://exslt.org/strings"
                extension-element-prefixes="str"
                exclude-result-prefixes="str">

    <xsl:template match="/">
        <soapEndpoint>
            <endpointName><xsl:value-of select="/sf:scifloConfig/sf:gridNamespace/text()"/></endpointName>
            <soapMethodSet>
                <soapMethod>
                    <exposedName><xsl:value-of select="/sf:scifloConfig/sf:addWorkUnitMethod/sf:exposedName"/></exposedName>
                    <pythonFunction><xsl:value-of select="/sf:scifloConfig/sf:addWorkUnitMethod/sf:pythonFunction"/></pythonFunction>
                </soapMethod>
                <soapMethod>
                    <exposedName><xsl:value-of select="/sf:scifloConfig/sf:queryWorkUnitMethod/sf:exposedName"/></exposedName>
                    <pythonFunction><xsl:value-of select="/sf:scifloConfig/sf:queryWorkUnitMethod/sf:pythonFunction"/></pythonFunction>
                </soapMethod>
                <soapMethod>
                    <exposedName><xsl:value-of select="/sf:scifloConfig/sf:cancelWorkUnitMethod/sf:exposedName"/></exposedName>
                    <pythonFunction><xsl:value-of select="/sf:scifloConfig/sf:cancelWorkUnitMethod/sf:pythonFunction"/></pythonFunction>
                </soapMethod>
                <soapMethod>
                    <exposedName><xsl:value-of select="/sf:scifloConfig/sf:callbackMethod/sf:exposedName"/></exposedName>
                    <pythonFunction><xsl:value-of select="/sf:scifloConfig/sf:callbackMethod/sf:pythonFunction"/></pythonFunction>
                </soapMethod>
            </soapMethodSet>
        </soapEndpoint>
    </xsl:template>

</xsl:transform>
