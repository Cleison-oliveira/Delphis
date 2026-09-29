{
  lib,
  stdenv,
  dotnetCorePackages,
  python3Packages,
  qt6,
  makeWrapper,
  makeDesktopItem,
  copyDesktopItems,
  dte,
  realesrgan-ncnn-vulkan,
  imagemagick,
  nvidia-texture-tools,
  vulkan-tools,
  vulkan-loader,
  src ? ../.,
}:
let
  desktopItem = makeDesktopItem {
    name = "delphis";
    exec = "delphis";
    icon = "delphis";
    desktopName = "Delphis";
    genericName = "Dolphin Texture Manipulation Tool";
    comment = "Extraction, Tonemaps, Alpha Transparency, AI Upscaling & DDS Optimization";
    categories = [
      "Utility"
      "Graphics"
      "Game"
    ];
    keywords = [
      "Dolphin"
      "Texture"
      "GameCube"
      "Wii"
      "Upscale"
      "DDS"
      "Tonemap"
    ];
  };

  pythonEnv = python3Packages.python.withPackages (
    ps: with ps; [
      pyqt6
      pillow
    ]
  );
in
stdenv.mkDerivation rec {
  pname = "delphis";
  version = lib.removeSuffix "\n" (builtins.readFile ../VERSION);

  inherit src;

  nativeBuildInputs = [
    dotnetCorePackages.sdk_8_0
    makeWrapper
    copyDesktopItems
    qt6.wrapQtAppsHook
  ];

  buildInputs = [
    dotnetCorePackages.runtime_8_0
    qt6.qtbase
    qt6.qtwayland
    qt6.qtsvg
    pythonEnv
  ];

  desktopItems = [ desktopItem ];

  buildPhase = ''
    runHook preBuild
    export DOTNET_CLI_TELEMETRY_OPTOUT=1
    export DOTNET_NOLOGO=1
    export HOME=$TMPDIR
    dotnet publish src/Delphis.Cli/Delphis.Cli.csproj -c Release -o $out/lib/delphis --no-self-contained
    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall
    mkdir -p $out/bin $out/lib/delphis_gui

    # Install Python GUI sources and VERSION file
    cp -r src/delphis_gui/* $out/lib/delphis_gui/
    cp VERSION $out/lib/delphis_gui/VERSION

    # 1. C# CLI Wrapper
    makeWrapper "${dotnetCorePackages.runtime_8_0}/bin/dotnet" $out/bin/delphis-cli \
      --add-flags "$out/lib/delphis/delphis-cli.dll" \
      --prefix PATH : ${lib.makeBinPath [
        dte
        realesrgan-ncnn-vulkan
        imagemagick
        nvidia-texture-tools
        vulkan-tools
        vulkan-loader
      ]}

    # 2. Main GUI Executable (PyQt6 calling C# backend)
    makeWrapper "${pythonEnv}/bin/python3" $out/bin/delphis \
      --add-flags "$out/lib/delphis_gui/main.py" \
      --set PYTHONPATH "$out/lib" \
      --prefix PATH : "$out/bin" \
      --prefix PATH : ${lib.makeBinPath [
        dte
        realesrgan-ncnn-vulkan
        imagemagick
        nvidia-texture-tools
        vulkan-tools
        vulkan-loader
      ]}

    install -Dm644 assets/icons/delphis.svg $out/share/icons/hicolor/scalable/apps/delphis.svg
    install -Dm644 assets/icons/delphis.svg $out/share/pixmaps/delphis.svg

    runHook postInstall
  '';

  dontWrapQtApps = false;

  preFixup = ''
    makeWrapperArgs+=("''${qtWrapperArgs[@]}")
  '';

  meta = with lib; {
    description = "Delphis: Dolphin Texture Manipulation Tool - Extraction, Tonemaps, Alpha Transparency, AI Upscaling & DDS Optimization";
    homepage = "https://github.com/Cleison-oliveira/delphis";
    license = licenses.mit;
    mainProgram = "delphis";
    platforms = platforms.linux;
  };
}
