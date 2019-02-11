<?xml version="1.0"?>
<xsl:transform version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:sf="http://sciflo.jpl.nasa.gov/2006v1/sf"
                xmlns:xf="http://www.w3.org/2002/xforms"
                xmlns:xs ="http://www.w3.org/2001/XMLSchema"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns="http://www.w3.org/1999/xhtml">

    <xsl:template match="/">
        <html>
            <head>
                <!--<title><xsl:value-of select="/sf:sciflo/sf:flow/sf:imports/sf:pythonMethods/sf:module/sf:url" /></title>-->
                <title><xsl:value-of select="/sf:sciflo/sf:flow/@name" /></title>
		<script type="text/javascript" src="http://sciflo.jpl.nasa.gov/genesis/test/js/formfaces.js"></script>
                <xf:model id="scifloXForm">
                    <xf:instance>
                        <sf:inputs>
                        <xsl:for-each select="/sf:sciflo/sf:flow/sf:inputs/*">
                            <xsl:call-template name="matchModel"/>
                        </xsl:for-each>
                        <xsl:for-each select="/sf:sciflo/sf:flow/sf:outputs/*">
                            <xsl:call-template name="matchModel"/>
                        </xsl:for-each>
                        </sf:inputs>
                    </xf:instance>
                    <!--<xf:submission id="scifloXForm" mediatype="application/xml" method="post" action="/sciflo/Private/SciFloWiki/runSciFloFromWiki" />-->
                    <xf:submission id="s1" method="post" action="http://sciflo.jpl.nasa.gov/genesis/cgi-bin/test.cgi" />
                </xf:model>
            </head>
            <body>
                <div class="form">
                    <font color="blue">
                    <p><b><xsl:value-of select="/sf:sciflo/sf:flow/@name"/></b></p>
                    <p><xsl:value-of select="/sf:sciflo/sf:flow/sf:description"/></p>
                    </font>
                    <p><b>Inputs:</b><br/>
                    <xsl:for-each select="/sf:sciflo/sf:flow/sf:inputs/*">
                        <xsl:call-template name="matchUI"/>
                    </xsl:for-each>
                    </p>
                    <p><b>Outputs:</b><br/>
                    <xsl:for-each select="/sf:sciflo/sf:flow/sf:outputs/*">
                        <xsl:call-template name="matchUI"/>
                    </xsl:for-each>
                    </p>
                    <xf:submit submission="s1">
                        <xf:label>Submit</xf:label>
                    </xf:submit>
                </div>
            </body>
        </html>
    </xsl:template>

    <xsl:template name="matchModel">
        <xsl:element name="{concat('sf:',local-name(.))}">
            <xsl:attribute name="xsi:type">
                <xsl:value-of select="@type"/>
            </xsl:attribute>
            <xsl:value-of select="."/>
        </xsl:element>
    </xsl:template>

    <xsl:template name="matchUI">
        <xsl:choose>
            <xsl:when test= "@type='xs:ISODateTime'">
                <xsl:element name="xf:input">
                    <xsl:attribute name="ref">
                        <xsl:value-of select="concat('/sf:inputs/sf:',local-name(.))"/>
                    </xsl:attribute>
                    <xsl:attribute name="model">scifloXForm</xsl:attribute>
                    <xsl:element name="xf:label">
                        <xsl:value-of select="concat(local-name(.),' (daterange): ')"/>
                    </xsl:element>
                    <xsl:element name="xf:hint">
                        Please enter a datetime.
                    </xsl:element>
                </xsl:element><br/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:element name="xf:input">
                    <xsl:attribute name="ref">
                        <xsl:value-of select="concat('/sf:inputs/sf:',local-name(.))"/>
                    </xsl:attribute>
                    <xsl:attribute name="model">scifloXForm</xsl:attribute>
                    <xsl:element name="xf:label">
                        <xsl:value-of select="concat(local-name(.),' (string): ')"/>
                    </xsl:element>
                    <xsl:element name="xf:hint">
                        Please enter a string.
                    </xsl:element>
                </xsl:element><br/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

</xsl:transform>
