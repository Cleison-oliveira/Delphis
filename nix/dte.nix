{
  lib,
  buildDotnetModule,
  dotnetCorePackages,
  makeWrapper,
  _7zz,
  src ? ../.,
}:
buildDotnetModule rec {
  pname = "dolphin-texture-extraction-tool";
  version = "1.8.0";

  inherit src;

  projectFile = "DolphinTextureExtraction/DolphinTextureExtraction.csproj";
  nugetDeps = ./deps.json;

  dotnet-sdk = dotnetCorePackages.sdk_8_0;
  dotnet-runtime = dotnetCorePackages.runtime_8_0;

  nativeBuildInputs = [
    makeWrapper
  ];

  runtimeDeps = [
    _7zz.lib
  ];

  postFixup = ''
    ln -s $out/bin/DolphinTextureExtraction.tool $out/bin/dte

    # Link 7-Zip native shared library for SevenZipExtractor archive support
    mkdir -p $out/lib/dolphin-texture-extraction-tool/x64
    ln -sf ${_7zz.lib}/lib/7z.so $out/lib/dolphin-texture-extraction-tool/7z-x64.dll || true
    ln -sf ${_7zz.lib}/lib/7z.so $out/lib/dolphin-texture-extraction-tool/7z.dll || true
    ln -sf ${_7zz.lib}/lib/7z.so $out/lib/dolphin-texture-extraction-tool/7z.so || true
    ln -sf ${_7zz.lib}/lib/7z.so $out/lib/dolphin-texture-extraction-tool/x64/7z.dll || true
    ln -sf ${_7zz.lib}/lib/7z.so $out/lib/dolphin-texture-extraction-tool/x64/7z.so || true
  '';

  meta = with lib; {
    description = "DolphinTextureExtraction-tool - Texture extraction, unpacking and combining tool for Dolphin textures";
    homepage = "https://github.com/Venomalia/DolphinTextureExtraction-tool";
    license = licenses.mit;
    mainProgram = "dte";
    platforms = platforms.linux;
  };
}
