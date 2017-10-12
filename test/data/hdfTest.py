#-----------------------------------------------------------------------------
# Name:        hdfTest.py
# Purpose:     Unit testing for hdf file access.
#
# Author:      Gerald Manipon
#
# Copyright:   (c) 2009, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os, shutil, unittest, urllib
from tempfile import mkdtemp

from sciflo.data.hdf import HdfFile

#http url to the same hdf file
fileUrl = 'http://sciflo.jpl.nasa.gov/genesis/unittestData/AIRS.2007.01.31.240.L2.RetStd.v5.0.14.0G07210145139.hdf'
fileUrl2 = 'http://sciflo.jpl.nasa.gov/genesis/unittestData/2007302214545_08003_CS_2B-CLDCLASS_GRANULE_P_R04_E02.hdf'
fileUrl3 = 'http://sciflo.jpl.nasa.gov/genesis/unittestData/2007302214545_08003_CS_2B-GEOPROF_GRANULE_P_R04_E02.hdf'

#assert xml
xml1 = '''<file xmlns="http://sciflo.jpl.nasa.gov/sciflo/namespaces/granuleMetadataXML-1.0" location="test.hdf" type="hdf4">
  <group name="L2_Standard_atmospheric&amp;surface_product">
    <dimension name="StdPressureLev" length="28"/>
    <dimension name="O3Func" length="9"/>
    <dimension name="GeoTrack" length="45"/>
    <dimension name="CH4Func" length="7"/>
    <dimension name="HingeSurf" length="100"/>
    <dimension name="AIRSTrack" length="3"/>
    <dimension name="H2OPressureLay" length="14"/>
    <dimension name="StdPressureLay" length="28"/>
    <dimension name="GeoXTrack" length="30"/>
    <dimension name="H2OFunc" length="11"/>
    <dimension name="Cloud" length="2"/>
    <dimension name="AIRSXTrack" length="3"/>
    <dimension name="COFunc" length="9"/>
    <dimension name="MWHingeSurf" length="7"/>
    <variable name="nStd_mid_top_bndry" shape="GeoTrack GeoXTrack" type="INT16">
      <attribute name="fill_value" value="-9999"/>
    </variable>
    <variable name="num_CO_Func" shape="GeoTrack GeoXTrack" type="INT16">
      <attribute name="fill_value" value="-9999"/>
    </variable>
    <variable name="ftptgeoqa" shape="GeoTrack GeoXTrack" type="UINT32">
      <attribute name="fill_value" value="4294967295"/>
    </variable>
    <variable name="Tdiff_IR_MW_ret" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="CO_VMR_eff_err" shape="GeoTrack GeoXTrack COFunc" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="emisIRStdErr" shape="GeoTrack GeoXTrack HingeSurf" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="TSurfAirErr" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Qual_Cloud_OLR" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="num_CH4_Func" shape="GeoTrack GeoXTrack" type="INT16">
      <attribute name="fill_value" value="-9999"/>
    </variable>
    <variable name="topog" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="CH4_verticality" shape="GeoTrack GeoXTrack CH4Func" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="H2O_verticality" shape="GeoTrack GeoXTrack H2OFunc" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Qual_MW_Only_Temp_Strat" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="Cloud_Resid_Ratio" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Qual_MW_Only_H2O" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="totH2OStdErr" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="num_H2O_Func" shape="GeoTrack GeoXTrack" type="INT16">
      <attribute name="fill_value" value="-9999"/>
    </variable>
    <variable name="CC1_noise_eff_amp_factor" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Longitude" shape="GeoTrack GeoXTrack" type="FLOAT64">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="PBest" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="CH4_eff_press" shape="GeoTrack GeoXTrack CH4Func" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="CldFrcStd" shape="GeoTrack GeoXTrack AIRSTrack AIRSXTrack Cloud" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="CH4_total_column" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="CO_total_column" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="TSurfStd" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="solazi" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Qual_H2O" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="EmisMWStd" shape="GeoTrack GeoXTrack MWHingeSurf" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="latAIRS" shape="GeoTrack GeoXTrack AIRSTrack AIRSXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="nStd_bot_mid_bndry" shape="GeoTrack GeoXTrack" type="INT16">
      <attribute name="fill_value" value="-9999"/>
    </variable>
    <variable name="MWSurfClass" shape="GeoTrack GeoXTrack" type="INT8"/>
    <variable name="GP_Height" shape="GeoTrack GeoXTrack StdPressureLev" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="olr" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Qual_Temp_Profile_Bot" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="H2OMMRSat" shape="GeoTrack GeoXTrack H2OPressureLay" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Latitude" shape="GeoTrack GeoXTrack" type="FLOAT64">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Tdiff_IR_4CC1" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="RetQAFlag" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="Qual_Surf" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="CH4_dof" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="TSurfStdErr" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Temp_Resid_Ratio" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="CC_noise_eff_amp_factor" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="CH4_VMR_eff" shape="GeoTrack GeoXTrack CH4Func" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Qual_CH4" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="Qual_CO" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="numCloud" shape="GeoTrack GeoXTrack" type="INT32">
      <attribute name="fill_value" value="-9999"/>
    </variable>
    <variable name="Qual_MW_Only_Temp_Tropo" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="CldFrcStdErr" shape="GeoTrack GeoXTrack AIRSTrack AIRSXTrack Cloud" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Qual_Temp_Profile_Top" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="Qual_Temp_Profile_Mid" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="PCldTopStd" shape="GeoTrack GeoXTrack Cloud" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="clrolr_err" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="CO_Resid_Ratio" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="satzen" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="zengeoqa" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="totH2OStd" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="CH4_VMR_eff_err" shape="GeoTrack GeoXTrack CH4Func" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="landFrac_err" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="PCldTopStdErr" shape="GeoTrack GeoXTrack Cloud" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="sfcTbMWStd" shape="GeoTrack GeoXTrack MWHingeSurf" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="PGood" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="spectral_clear_indicator" shape="GeoTrack GeoXTrack AIRSTrack AIRSXTrack" type="INT16">
      <attribute name="fill_value" value="-9999"/>
    </variable>
    <variable name="TCldTopStd" shape="GeoTrack GeoXTrack Cloud" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="totCldH2OStdErr" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="num_O3_Func" shape="GeoTrack GeoXTrack" type="INT16">
      <attribute name="fill_value" value="-9999"/>
    </variable>
    <variable name="CCfinal_Resid" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="totO3Std" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="num_clear_spectral_indicator" shape="GeoTrack GeoXTrack" type="INT16">
      <attribute name="fill_value" value="-9999"/>
    </variable>
    <variable name="olr_err" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="PSurfStd" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="EmisMWStdErr" shape="GeoTrack GeoXTrack MWHingeSurf" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="landFrac" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="CO_dof" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="solzen" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="TAirMWOnlyStd" shape="GeoTrack GeoXTrack StdPressureLev" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="PTropopause" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="GP_Tropopause" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="CC1_Resid" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="CO_VMR_eff" shape="GeoTrack GeoXTrack COFunc" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="TotCld_4_CCfinal" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="TCldTopStdErr" shape="GeoTrack GeoXTrack Cloud" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="totO3StdErr" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="dust_flag" shape="GeoTrack GeoXTrack AIRSTrack AIRSXTrack" type="INT16">
      <attribute name="fill_value" value="-9999"/>
    </variable>
    <variable name="TAirStdErr" shape="GeoTrack GeoXTrack StdPressureLev" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="GP_Surface" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Qual_clrolr" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="TAirStd" shape="GeoTrack GeoXTrack StdPressureLev" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Initial_CC_score" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="H2OMMRSat_liquid" shape="GeoTrack GeoXTrack H2OPressureLay" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="O3VMRStdErr" shape="GeoTrack GeoXTrack StdPressureLay" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Press_mid_top_bndry" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Time" shape="GeoTrack GeoXTrack" type="FLOAT64">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="totCldH2OStd" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="H2OMMRStd" shape="GeoTrack GeoXTrack H2OPressureLay" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Surf_Resid_Ratio" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="nGoodStd" shape="GeoTrack GeoXTrack" type="INT16">
      <attribute name="fill_value" value="-9999"/>
    </variable>
    <variable name="nBestStd" shape="GeoTrack GeoXTrack" type="INT16">
      <attribute name="fill_value" value="-9999"/>
    </variable>
    <variable name="TSurfAir" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Startup" shape="GeoTrack GeoXTrack" type="INT8"/>
    <variable name="O3_dof" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="nSurfStd" shape="GeoTrack GeoXTrack" type="INT32">
      <attribute name="fill_value" value="-9999"/>
    </variable>
    <variable name="O3VMRStd" shape="GeoTrack GeoXTrack StdPressureLay" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="CO_verticality" shape="GeoTrack GeoXTrack COFunc" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Qual_Guess_PSurf" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="CCfinal_Noise_Amp" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="clrolr" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="sun_glint_distance" shape="GeoTrack GeoXTrack" type="INT16">
      <attribute name="fill_value" value="-9999"/>
    </variable>
    <variable name="totH2OMWOnlyStd" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Qual_O3" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="H2OMMRStdErr" shape="GeoTrack GeoXTrack H2OPressureLay" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="CH4_Resid_Ratio" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Press_bot_mid_bndry" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="O3_verticality" shape="GeoTrack GeoXTrack O3Func" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="MW_ret_used" shape="GeoTrack GeoXTrack" type="INT8"/>
    <variable name="AMSU_Chans_Resid" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="satazi" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="TSurfdiff_IR_4CC2" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="TSurfdiff_IR_4CC1" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="emisIRStd" shape="GeoTrack GeoXTrack HingeSurf" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="freqEmis" shape="GeoTrack GeoXTrack HingeSurf" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="all_spots_avg" shape="GeoTrack GeoXTrack" type="INT8"/>
    <variable name="numHingeSurf" shape="GeoTrack GeoXTrack" type="INT16">
      <attribute name="fill_value" value="-9999"/>
    </variable>
    <variable name="T_Tropopause" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="GP_Height_MWOnly" shape="GeoTrack GeoXTrack StdPressureLev" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="MWCheck_Resid_Ratio" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="retrieval_type" shape="GeoTrack GeoXTrack" type="INT8"/>
    <variable name="topog_err" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="lonAIRS" shape="GeoTrack GeoXTrack AIRSTrack AIRSXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="demgeoqa" shape="GeoTrack GeoXTrack" type="UINT16">
      <attribute name="fill_value" value="65534"/>
    </variable>
    <variable name="CO_eff_press" shape="GeoTrack GeoXTrack COFunc" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="Water_Resid_Ratio" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
    <variable name="O3_Resid_Ratio" shape="GeoTrack GeoXTrack" type="FLOAT32">
      <attribute name="fill_value" value="-9999.0"/>
    </variable>
  </group>
</file>\n'''

xml2 = '''<file xmlns="http://sciflo.jpl.nasa.gov/sciflo/namespaces/granuleMetadataXML-1.0" location="test.hdf" type="hdf4">
  <group name="2B-CLDCLASS">
    <dimension name="nbin" length="125"/>
    <dimension name="nray" length="37082"/>
    <variable name="cloud_scenario" shape="nray nbin" type="INT16">
      <attribute name="units" value="none"/>
      <attribute name="long_name" value="Cloud scenario"/>
      <attribute name="offset" value="0.0"/>
      <attribute name="valid_range" value="[0, 32767]"/>
      <attribute name="factor" value="1.0"/>
    </variable>
    <variable name="Height" shape="nray nbin" type="INT16">
      <attribute name="fill_value" value="-9999"/>
      <attribute name="missop" value="=="/>
      <attribute name="missing" value="-9999"/>
      <attribute name="factor" value="1.0"/>
      <attribute name="valid_range" value="[-5000, 30000]"/>
      <attribute name="long_name" value="Height of range bin in Reflectivity/Cloud Mask above reference surface (~ mean sea level)."/>
      <attribute name="offset" value="0.0"/>
      <attribute name="units" value="m"/>
    </variable>
  </group>
</file>\n'''

xml3 = '''<file xmlns="http://sciflo.jpl.nasa.gov/sciflo/namespaces/granuleMetadataXML-1.0" location="test.hdf" type="hdf4">
  <group name="2B-GEOPROF">
    <dimension name="nbin" length="125"/>
    <dimension name="nray" length="37082"/>
    <variable name="Height" shape="nray nbin" type="INT16">
      <attribute name="fill_value" value="-9999"/>
      <attribute name="missop" value="=="/>
      <attribute name="missing" value="-9999"/>
      <attribute name="factor" value="1.0"/>
      <attribute name="valid_range" value="[-5000, 30000]"/>
      <attribute name="long_name" value="Height of range bin in Reflectivity/Cloud Mask above reference surface (~ mean sea level)."/>
      <attribute name="offset" value="0.0"/>
      <attribute name="units" value="m"/>
    </variable>
    <variable name="CPR_Cloud_mask" shape="nray nbin" type="INT8">
      <attribute name="fill_value" value="-99"/>
      <attribute name="missop" value="=="/>
      <attribute name="missing" value="-9"/>
      <attribute name="factor" value="1.0"/>
      <attribute name="valid_range" value="[0, 40]"/>
      <attribute name="long_name" value="CPR Cloud Mask"/>
      <attribute name="offset" value="0.0"/>
    </variable>
    <variable name="Gaseous_Attenuation" shape="nray nbin" type="INT16">
      <attribute name="fill_value" value="15360"/>
      <attribute name="missop" value="=="/>
      <attribute name="missing" value="-9999"/>
      <attribute name="factor" value="100.0"/>
      <attribute name="valid_range" value="[0, 1000]"/>
      <attribute name="long_name" value="Gaseous_Attenuation"/>
      <attribute name="offset" value="0.0"/>
      <attribute name="units" value="dBZe"/>
    </variable>
    <variable name="Radar_Reflectivity" shape="nray nbin" type="INT16">
      <attribute name="fill_value" value="15360"/>
      <attribute name="missop" value="=="/>
      <attribute name="missing" value="-8888"/>
      <attribute name="factor" value="100.0"/>
      <attribute name="valid_range" value="[-4000, 5000]"/>
      <attribute name="long_name" value="Radar Reflectivity Factor"/>
      <attribute name="offset" value="0.0"/>
      <attribute name="units" value="dBZe"/>
    </variable>
  </group>
</file>\n'''

class hdfTestCase(unittest.TestCase):
    """Test case for sciflo.data.hdf."""

    def setUp(self):
        self.tempDir = mkdtemp()
        
    def testHdfFile(self):
        """Test HdfFile class on AIRS v5 L2 RetStd."""

        #local hdf file
        hdffile, hdffile_fh = urllib.urlretrieve(fileUrl, os.path.join(self.tempDir, 'test.hdf'))

        #HdfFile object
        h = HdfFile(hdffile)
        self.assertEquals(h.getMetadataXml(), xml1)
        
    def testHdfFile2(self):
        """Test HdfFile class on CloudSat CLDCLASS."""

        #local hdf file
        hdffile, hdffile_fh = urllib.urlretrieve(fileUrl2, os.path.join(self.tempDir, 'test.hdf'))

        #HdfFile object
        h = HdfFile(hdffile)
        self.assertEquals(h.getMetadataXml(), xml2)
        
    def testHdfFile3(self):
        """Test HdfFile class on CloudSat GEOPROF."""

        #local hdf file
        hdffile, hdffile_fh = urllib.urlretrieve(fileUrl3, os.path.join(self.tempDir, 'test.hdf'))

        #HdfFile object
        h = HdfFile(hdffile)
        self.assertEquals(h.getMetadataXml(), xml3)
        
    def tearDown(self):
        shutil.rmtree(self.tempDir)

#create testsuite function
def getTestSuite():
    """Creates and returns a test suite."""
    #run tests
    hdfTestSuite = unittest.TestSuite()
    hdfTestSuite.addTest(hdfTestCase("testHdfFile"))
    hdfTestSuite.addTest(hdfTestCase("testHdfFile2"))
    hdfTestSuite.addTest(hdfTestCase("testHdfFile3"))

    #return
    return hdfTestSuite

#main
if __name__ == "__main__":

    #get testSuite
    testSuite=getTestSuite()

    #run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)
