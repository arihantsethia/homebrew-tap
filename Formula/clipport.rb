class Clipport < Formula
  desc "Paste local clipboard text and screenshots into remote iTerm SSH sessions"
  homepage "https://github.com/arihantsethia/clipport"
  url "https://github.com/arihantsethia/clipport/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "e04a80d267bf4acdb8d7dd14b7e7cdab0c2a648292d4285affc51194c5f5b470"
  license "MIT"
  revision 3
  head "https://github.com/arihantsethia/clipport.git", branch: "main"

  depends_on "go" => :build
  depends_on :macos
  depends_on "pngpaste"

  def install
    system "go", "build", "-o", bin/"clipctl", "./cmd/clipctl"
    system "go", "build", "-o", bin/"clipportd", "./cmd/clipportd"
    system "go", "build", "-o", bin/"clipport", "./cmd/clipport"

    app = libexec/"Clipport.app"
    (app/"Contents/MacOS").mkpath
    (app/"Contents/Resources").mkpath
    cp bin/"clipport", app/"Contents/MacOS/clipport"
    chmod 0755, app/"Contents/MacOS/clipport"
    (app/"Contents/Resources").install "cmd/clipport/assets/app.icns" => "Clipport.icns"

    (app/"Contents/Info.plist").write <<~XML
      <?xml version="1.0" encoding="UTF-8"?>
      <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
      <plist version="1.0">
      <dict>
        <key>CFBundleExecutable</key>
        <string>clipport</string>
        <key>CFBundleIdentifier</key>
        <string>com.clipport.app</string>
        <key>CFBundleName</key>
        <string>Clipport</string>
        <key>CFBundleDisplayName</key>
        <string>Clipport</string>
        <key>CFBundleIconFile</key>
        <string>Clipport.icns</string>
        <key>CFBundlePackageType</key>
        <string>APPL</string>
        <key>CFBundleVersion</key>
        <string>#{version}</string>
        <key>CFBundleShortVersionString</key>
        <string>#{version}</string>
        <key>LSUIElement</key>
        <string>1</string>
        <key>NSHighResolutionCapable</key>
        <string>True</string>
      </dict>
      </plist>
    XML

    (libexec/"com.clipport.app.plist").write <<~XML
      <?xml version="1.0" encoding="UTF-8"?>
      <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
      <plist version="1.0">
      <dict>
        <key>Label</key>
        <string>com.clipport.app</string>
        <key>ProgramArguments</key>
        <array>
          <string>#{opt_libexec}/Clipport.app/Contents/MacOS/clipport</string>
        </array>
        <key>RunAtLoad</key>
        <true/>
        <key>StandardOutPath</key>
        <string>/tmp/clipport.out.log</string>
        <key>StandardErrorPath</key>
        <string>/tmp/clipport.err.log</string>
      </dict>
      </plist>
    XML

    (bin/"clipport-setup").write <<~SH
      #!/bin/sh
      set -eu

      app_link="$HOME/Applications/Clipport.app"
      app_target="#{opt_libexec}/Clipport.app"
      mkdir -p "$HOME/Applications"
      if [ -L "$app_link" ]; then
        rm "$app_link"
      fi
      if [ -e "$app_link" ]; then
        bundle_id=$(/usr/libexec/PlistBuddy -c "Print :CFBundleIdentifier" "$app_link/Contents/Info.plist" 2>/dev/null || true)
        if [ "$bundle_id" = "com.clipport.app" ]; then
          rm -rf "$app_link"
        else
          echo "clipport: $app_link already exists and is not Clipport" >&2
          exit 1
        fi
      fi
      ln -s "$app_target" "$app_link"
      lsregister="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
      if [ -x "$lsregister" ]; then
        "$lsregister" -f "$app_link" >/dev/null 2>&1 || true
      fi

      config_path="${CLIPPORT_CONFIG:-$HOME/.config/clipport/config.toml}"
      http_args=""
      if [ ! -f "$config_path" ]; then
        port=18765
        while [ "$port" -le 18865 ]; do
          if ! lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
            break
          fi
          port=$((port + 1))
        done
        if [ "$port" -gt 18865 ]; then
          echo "clipport: no free loopback HTTP port found in 18765-18865" >&2
          exit 1
        fi
        http_args="--http 127.0.0.1:$port"
      fi

      exec "#{opt_bin}/clipctl" install-record \\
        --config "$config_path" \\
        --bin-dir "#{opt_bin}" \\
        --app-launchd-plist "#{opt_libexec}/com.clipport.app.plist" \\
        --app-path "$app_link" \\
        $http_args \\
        --iterm-key "0x76-0x120000"
    SH
    chmod 0755, bin/"clipport-setup"
  end

  def caveats
    <<~EOS
      Finish setup with:
        clipport-setup
        clipctl onboard
        clipctl start
        clipctl doctor
    EOS
  end

  test do
    assert_match "usage: clipctl", shell_output("#{bin}/clipctl help 2>&1")
    assert_match "install-record", shell_output("grep install-record #{bin}/clipport-setup")
    assert_match "clipport: use clipctl paste", shell_output("#{bin}/clipport paste 2>&1", 2)
  end
end
