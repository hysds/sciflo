#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Name:        subset.py
# Purpose:     Aeronet rdb subset functions.
#
# Author:      Zhangfan Xing
#
# Created:     Mon Aug 14 14:42:40 2006
# Copyright:   (c) 2006, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import sys
import MySQLdb as db

# standard variable names
DATA_VARS = [
'AOT_1640', 'AOT_1020', 'AOT_870', 'AOT_675', 'AOT_667',
'AOT_555', 'AOT_551', 'AOT_532', 'AOT_531', 'AOT_500',
'AOT_490', 'AOT_443', 'AOT_440', 'AOT_412', 'AOT_380',
'AOT_340'
]

# particle properties
DATA_VARS_EXTRA = [
'AOT_1640',
'AOT_1020',
'AOT_870',
'AOT_675',
'AOT_667',
'AOT_555',
'AOT_551',
'AOT_532',
'AOT_531',
'AOT_500',
'AOT_490',
'AOT_443',
'AOT_440',
'AOT_412',
'AOT_380',
'AOT_340',
'Water_cm',
'AOTExt440minusT',
'AOTExt670minusT',
'AOTExt868minusT',
'AOTExt1020minusT',
'AOTExt440minusF',
'AOTExt670minusF',
'AOTExt871minusF',
'AOTExt1018minusF',
'AOTExt440minusC',
'AOTExt674minusC',
'AOTExt870minusC',
'AOTExt1020minusC',
'_870to440AngstromParam_AOTExt_minusTotal',
'SSA440minusT',
'SSA674minusT',
'SSA868minusT',
'SSA1020minusT',
'AOTAbsp442minusT',
'AOTAbsp675minusT',
'AOTAbsp868minusT',
'AOTAbsp1020minusT',
'_870to440AngstromParam_AOTAbsp_',
'REFR_440_',
'REFR_674_',
'REFR_869_',
'REFR_1020_',
'REFI_439_',
'REFI_670_',
'REFI_871_',
'REFI_1020_',
'ASYM441minusT',
'ASYM677minusT',
'ASYM870minusT',
'ASYM1020minusT',
'ASYM442minusF',
'ASYM677minusF',
'ASYM868minusF',
'ASYM1020minusF',
'ASYM440minusC',
'ASYM670minusC',
'ASYM869minusC',
'ASYM1022minusC',
'Inflection_Point_um_',
'VolConMinusT',
'EffRadMinusT',
'VolMedianRadMinusT',
'StdDevMinusT',
'VolConMinusF',
'EffRadMinusF',
'VolMedianRadMinusF',
'StdDevMinusF',
'VolConMinusC',
'EffRadMinusC',
'VolMedianRadMinusC',
'StdDevMinusC',
'Altitude_BOA__km_',
'Altitude_TOA__km_',
'DownwardFlux_BOA_',
'DownwardFlux_TOA_',
'UpwardFlux_BOA_',
'UpwardFlux_TOA_',
'RadiativeForcing_BOA_',
'RadiativeForcing_TOA_',
'ForcingEfficiency_BOA_',
'ForcingEfficiency_TOA_',
'DownwardFlux442minusT',
'DownwardFlux669minusT',
'DownwardFlux869minusT',
'DownwardFlux1018minusT',
'UpwardFlux440minusT',
'UpwardFlux677minusT',
'UpwardFlux870minusT',
'UpwardFlux1020minusT',
'DiffuseFlux442minusT',
'DiffuseFlux675minusT',
'DiffuseFlux869minusT',
'DiffuseFlux1020minusT',
'solar_zenith_angle',
'sky_error',
'sun_error',
'alpha440to870',
'tau440_measured_',
'_sphericity',
'scat_angle_440_ge3dot2to6_',
'scat_angle_440_ge6to30_',
'scat_angle_440_ge30to80_',
'scat_angle_440_ge80_',
'scat_angle_675_ge3dot2to6_',
'scat_angle_675_ge6to30_',
'scat_angle_675_ge30to80_',
'scat_angle_675_ge80_',
'scat_angle_870_ge3dot2to6_',
'scat_angle_870_ge6to30_',
'scat_angle_870_ge30to80_',
'scat_angle_870_ge80_',
'scat_angle_1020_ge3dot2to6_',
'scat_angle_1020_ge6to30_',
'scat_angle_1020_ge30to80_',
'scat_angle_1020_ge80_',
'albedo_440',
'albedo_675',
'albedo_870',
'albedo_1020',
]

def parse(dburi):
    """ Parse dburi, format is username:password@host:port/db """

    # default
    username = ""
    password = ""
    host = "127.0.0.1"
    port = 3306
    dbname = "aeronet"

    # 20070926, xing fixme: error checking here?
    auth, location = dburi.split('@')

    username, password = auth.split(':')

    hostport, dbname = location.split('/')
    host, port = hostport.split(':')
    port = int(port)

    return host, port, username, password, dbname


def subset(dburi, metaTable, dataTable, vars,
    dt0, dt1, lat0, lat1, lon0, lon1):
    """ Subset vars on all sites for given time range, lat and lon domain. """
    return subsetOneSite(dburi, metaTable, dataTable, vars, None,
        dt0, dt1, lat0, lat1, lon0, lon1)

def subsetOneSite(dburi, metaTable, dataTable, vars, fname,
        dt0, dt1, lat0, lat1, lon0, lon1):
    """ Subset vars on one site by field fname
        for given time range, lat and lon domain.
    """

    # set db conn
    host, port, username, password, dbname = parse(dburi)
    conn = db.connect(host=host, port=port, user=username, passwd=password, db=dbname)
    cursor = conn.cursor()

    query = "SELECT " \
        + ("","fname, ")[fname==None] + "dt, lon, lat, %s" % (', '.join(vars)) \
        + " FROM %s, %s" % (metaTable, dataTable) \
        + " WHERE " + ("fname='%s' AND" % (fname), "")[fname==None] \
        + " %s.fid = %s.fid" % (metaTable, dataTable) \
        + " AND (dt BETWEEN '%s' AND '%s') " % (dt0, dt1) \
        + " AND (lon BETWEEN %s AND %s) " % (lon0, lon1) \
        + " AND (lat BETWEEN %s AND %s) " % (lat0, lat1) \
        + " ORDER BY dt"
    #print >>sys.stderr, "subset query: %s" % query

    # execute query
    cursor.execute(query)
    rows = cursor.fetchall()
    #desc = cursor.description
    cursor.close()
    conn.close()

    return rows

def main():

    if (len(sys.argv) != 11):
        sys.stderr.write("Usage: " + sys.argv[0]
            + " dburi metaTable dataTable var dt0 dt1 lat0 lat1 lon0 lon1\n")
        sys.exit(1)

    dburi, metaTable, dataTable, var, dt0, dt1, lat0, lat1, lon0, lon1 = sys.argv[1:]

    for x in subset(dburi, metaTable, dataTable, var, dt0, dt1, lat0, lat1, lon0, lon1):
        print x


if __name__ == "__main__":
  main()
