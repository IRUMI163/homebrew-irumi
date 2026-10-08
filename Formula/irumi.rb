class Irumi < Formula
  desc "日本語語順スクリプト言語 IRUMI (SOV Japanese Scripting Language)"
  homepage "https://github.com/IRUMI163/homebrew-irumi"
  url "https://github.com/IRUMI163/homebrew-irumi.git", branch: "main"
  version "1.0.0"
  license "MIT"

  def install
    bin.install "irumi"
    bin.install "irumi.py"
  end

  test do
    system "#{bin}/irumi", "-v"
  end
end
