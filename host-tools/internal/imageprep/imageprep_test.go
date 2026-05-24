package imageprep

import (
	"context"
	"image"
	"image/color"
	"image/png"
	"os"
	"path/filepath"
	"testing"
)

func TestPrepareFileConvertsSourceToGray(t *testing.T) {
	t.Parallel()

	tempDir := t.TempDir()
	inputPath := filepath.Join(tempDir, "input.png")

	source := image.NewNRGBA(image.Rect(0, 0, 2, 1))
	source.Set(0, 0, color.NRGBA{R: 255, A: 255})
	source.Set(1, 0, color.NRGBA{B: 255, A: 255})

	writeTestPNG(t, inputPath, source)

	prepared, err := NewService().PrepareFile(context.Background(), inputPath, Options{Threshold: -1})
	if err != nil {
		t.Fatalf("PrepareFile() error = %v", err)
	}

	redGray := color.GrayModel.Convert(color.NRGBA{R: 255, A: 255}).(color.Gray)
	blueGray := color.GrayModel.Convert(color.NRGBA{B: 255, A: 255}).(color.Gray)

	if got := prepared.Bitmap.GrayAt(0, 0); got != redGray {
		t.Fatalf("GrayAt(0, 0) = %#v, want %#v", got, redGray)
	}
	if got := prepared.Bitmap.GrayAt(1, 0); got != blueGray {
		t.Fatalf("GrayAt(1, 0) = %#v, want %#v", got, blueGray)
	}
}

func TestPrepareFileThresholdsBitmap(t *testing.T) {
	t.Parallel()

	tempDir := t.TempDir()
	inputPath := filepath.Join(tempDir, "threshold.png")

	source := image.NewGray(image.Rect(0, 0, 2, 1))
	source.SetGray(0, 0, color.Gray{Y: 100})
	source.SetGray(1, 0, color.Gray{Y: 200})

	writeTestPNG(t, inputPath, source)

	prepared, err := NewService().PrepareFile(context.Background(), inputPath, Options{Threshold: 128})
	if err != nil {
		t.Fatalf("PrepareFile() error = %v", err)
	}

	if got := prepared.Bitmap.GrayAt(0, 0); got.Y != 0x00 {
		t.Fatalf("GrayAt(0, 0) = %d, want 0", got.Y)
	}
	if got := prepared.Bitmap.GrayAt(1, 0); got.Y != 0xff {
		t.Fatalf("GrayAt(1, 0) = %d, want 255", got.Y)
	}
}

func writeTestPNG(t *testing.T, path string, source image.Image) {
	t.Helper()

	file, err := os.Create(path)
	if err != nil {
		t.Fatalf("os.Create(%q): %v", path, err)
	}
	defer file.Close()

	if err := png.Encode(file, source); err != nil {
		t.Fatalf("png.Encode(%q): %v", path, err)
	}
}