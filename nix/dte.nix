{
  lib,
  stdenv,
  fetchurl,
  unzip,
  autoPatchelfHook,
  makeWrapper,
  libx11,
  libxi,
  libxcursor,
  libxrandr,
  libxxf86vm,
  libglvnd,
  glfw,
  zlib,
  icu,
  openssl,
  libunwind,
  libuuid,
  util-linux,
  dotnetCorePackages,
  _7zz,
}:
stdenv.mkDerivation rec {
  pname = "dolphin-texture-extraction-tool";
  version = "1.8.0";

  src = fetchurl {
    url = "https://github.com/Venomalia/DolphinTextureExtraction-tool/releases/download/${version}/linux-x64.zip";
    sha256 = "sha256-/6aUzD3lkiDrbtD/BWjEQ9pG3MN0r/3UcsnInW6p54w=";
  };

  nativeBuildInputs = [
    unzip
    autoPatchelfHook
    makeWrapper
  ];

  buildInputs = [
    stdenv.cc.cc.lib
    libx11
    libxi
    libxcursor
    libxrandr
    libxxf86vm
    libglvnd
    glfw
    zlib
    icu
    openssl
    libunwind
    libuuid
    util-linux
    dotnetCorePackages.runtime_8_0
    _7zz.lib
  ];

  unpackPhase = ''
    runHook preUnpack
    unzip -q $src -d dte-unpacked
    sourceRoot=dte-unpacked
    runHook postUnpack
  '';

  installPhase = ''
    runHook preInstall
    mkdir -p $out/lib/dte/x64 $out/bin

    cp -r ./* $out/lib/dte/
    chmod +x $out/lib/dte/libglfw.so.3.3 || true
    chmod +x $out/lib/dte/libnironcompress.so || true

    # Link 7-Zip native shared library for SevenZipExtractor archive support
    ln -sf ${_7zz.lib}/lib/7z.so $out/lib/dte/7z-x64.dll
    ln -sf ${_7zz.lib}/lib/7z.so $out/lib/dte/7z.dll
    ln -sf ${_7zz.lib}/lib/7z.so $out/lib/dte/7z.so
    ln -sf ${_7zz.lib}/lib/7z.so $out/lib/dte/x64/7z.dll
    ln -sf ${_7zz.lib}/lib/7z.so $out/lib/dte/x64/7z.so

    DOTNET_RUNTIME=${dotnetCorePackages.runtime_8_0}

    cat > $out/lib/dte/DolphinTextureExtraction.tool.runtimeconfig.json << 'RUNTIMECONFIG'
{
  "runtimeOptions": {
    "tfm": "net6.0",
    "rollForward": "LatestMajor",
    "framework": {
      "name": "Microsoft.NETCore.App",
      "version": "6.0.0"
    },
    "configProperties": {
      "System.Reflection.Metadata.MetadataUpdater.IsSupported": false
    }
  }
}
RUNTIMECONFIG

    makeWrapper "$DOTNET_RUNTIME/bin/dotnet" $out/bin/dte \
      --add-flags "$out/lib/dte/DolphinTextureExtraction.tool.dll" \
      --set DOTNET_ROLL_FORWARD "LatestMajor" \
      --prefix LD_LIBRARY_PATH : "$out/lib/dte" \
      --prefix LD_LIBRARY_PATH : "$out/lib/dte/x64" \
      --prefix LD_LIBRARY_PATH : "${_7zz.lib}/lib" \
      --prefix LD_LIBRARY_PATH : "$DOTNET_RUNTIME/lib"

    ln -s $out/bin/dte $out/bin/DolphinTextureExtraction.tool

    runHook postInstall
  '';

  dontBuild = true;
  dontConfigure = true;
  doCheck = false;

  meta = with lib; {
    description = "DolphinTextureExtraction-tool - Texture extraction, unpacking and combining tool for Dolphin textures";
    homepage = "https://github.com/Venomalia/DolphinTextureExtraction-tool";
    license = licenses.mit;
    mainProgram = "dte";
    platforms = [ "x86_64-linux" ];
  };
}
