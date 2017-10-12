<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           elementFormDefault="qualified"
           targetNamespace="http://sciflo.jpl.nasa.gov/2006v1/sf"
           xmlns:sf="http://sciflo.jpl.nasa.gov/2006v1/sf"
           xmlns:py="http://sciflo.jpl.nasa.gov/2006v1/py">
  <xs:element name="sciflo">
    <xs:annotation>
      <xs:documentation>Sciflo xml document root element.</xs:documentation>
    </xs:annotation>
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="sf:flow"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
  <xs:element name="flow">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="sf:title" minOccurs="0" maxOccurs="1"/>
        <xs:element ref="sf:icon" minOccurs="0" maxOccurs="1"/>
        <xs:element ref="sf:description"/>
        <xs:element ref="sf:inputs"/>
        <xs:element ref="sf:outputs"/>
        <xs:element ref="sf:processes"/>
      </xs:sequence>
      <xs:attribute name="id" type="xs:string" use="required"/>
      <xs:attribute name="version" type="xs:string" use="optional"/>
    </xs:complexType>
  </xs:element>
  <xs:element name="title" type="xs:string"/>
  <xs:element name="icon" type="xs:string"/>
  <xs:element name="description" type="xs:string"/>
  <xs:element name="inputs">
    <xs:complexType>
      <xs:sequence>
        <xs:any minOccurs="0" maxOccurs="unbounded" processContents="lax"/>
      </xs:sequence>
      <xs:attribute name="type" type="xs:string" use="optional"/>
      <xs:attribute name="view" type="xs:string" use="optional"/>
      <xs:attribute name="group" type="xs:string" use="optional"/>
    </xs:complexType>
  </xs:element>
  <xs:element name="outputs">
    <xs:complexType>
      <xs:sequence>
        <xs:any minOccurs="0" maxOccurs="unbounded" processContents="lax"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
  <xs:element name="processes">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="sf:process" maxOccurs="unbounded"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
  <xs:element name="process">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="sf:inputs"/>
        <xs:element ref="sf:outputs"/>
        <xs:element ref="sf:operator"/>
      </xs:sequence>
      <xs:attribute name="id" type="xs:string" use="required"/>
      <xs:attribute name="kind" type="xs:string" use="optional"/>
      <xs:attribute name="group" type="xs:string" use="optional"/>
      <xs:attribute name="optional" type="xs:string" use="optional"/>
      <xs:attribute name="paletteIcon" type="xs:string" use="optional"/>
    </xs:complexType>
  </xs:element>
  <xs:element name="operator">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="sf:description" minOccurs="0" maxOccurs="1"/>
        <xs:element ref="sf:op" minOccurs="1" maxOccurs="unbounded"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
  <xs:element name="op">
    <xs:complexType>
      <xs:sequence>
        <xs:choice>
          <xs:element ref="sf:binding" minOccurs="1" maxOccurs="1"/>
        </xs:choice>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
  <xs:element name="binding">
    <xs:complexType mixed="true">
      <xs:sequence>
        <xs:element ref="sf:bind" minOccurs="0" maxOccurs="1"/>
        <xs:element ref="sf:headers" minOccurs="0" maxOccurs="1"/>
      </xs:sequence>
      <xs:attribute name="job_queue" type="xs:string" use="optional"/>
      <xs:attribute name="async" type="xs:string" use="optional"/>
    </xs:complexType>
  </xs:element>
  <xs:element name="bind" type="xs:string"/>
  <xs:element name="headers">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="sf:header" maxOccurs="unbounded"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
  <xs:element name="header">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="sf:name" minOccurs="1" maxOccurs="1"/>
        <xs:element ref="sf:value" minOccurs="1" maxOccurs="1"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
  <xs:element name="name" type="xs:string"/>
  <xs:element name="value" type="xs:string"/>
</xs:schema>
