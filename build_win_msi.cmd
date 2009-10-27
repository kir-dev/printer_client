
"%WIX%bin\candle.exe" -nologo printer-client.wxs -out printer-client.wixobj
"%WIX%bin\light.exe" "printer-client.wixobj" -out "Kir-Dev Printer Client.msi" -ext WixUIExtension -cultures:hu-hu

rem Cleanup

del *.wixobj /Q
del *.wixpdb /Q
