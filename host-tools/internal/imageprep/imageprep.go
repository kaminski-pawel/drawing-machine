package imageprep

import (
	"context"
	"fmt"
	"image"
	"image/color"
	"image/png"
	"os"

	_ "image/jpeg"
	_ "image/png"
)

type Options struct {
	Threshold int
}

type PreparedImage struct {
	SourcePath string
	Bitmap     *image.Gray
}

type Preparer interface {
	PrepareFile(ctx context.Context, inputPath string, options Options) (*PreparedImage, error)
}

type Service struct{}

func NewService() Service {
	return Service{}
}

func (Service) PrepareFile(ctx context.Context, inputPath string, options Options) (*PreparedImage, error) {
	select {
	case <-ctx.Done():
		return nil, fmt.Errorf("prepare image %s: %w", inputPath, ctx.Err())
	default:
	}

	file, err := os.Open(inputPath)
	if err != nil {
		return nil, fmt.Errorf("open input image %s: %w", inputPath, err)
	}
	defer file.Close()

	source, _, err := image.Decode(file)
	if err != nil {
		return nil, fmt.Errorf("decode input image %s: %w", inputPath, err)
	}

	gray := image.NewGray(source.Bounds())
	for y := source.Bounds().Min.Y; y < source.Bounds().Max.Y; y++ {
		for x := source.Bounds().Min.X; x < source.Bounds().Max.X; x++ {
			pixel := color.GrayModel.Convert(source.At(x, y)).(color.Gray)
			if options.Threshold >= 0 {
				if pixel.Y >= uint8(options.Threshold) {
					pixel.Y = 0xff
				} else {
					pixel.Y = 0x00
				}
			}
			gray.SetGray(x, y, pixel)
		}
	}

	return &PreparedImage{
		SourcePath: inputPath,
		Bitmap:     gray,
	}, nil
}

func WritePNG(outputPath string, bitmap *image.Gray) error {
	file, err := os.Create(outputPath)
	if err != nil {
		return fmt.Errorf("create output image %s: %w", outputPath, err)
	}
	defer file.Close()

	if err := png.Encode(file, bitmap); err != nil {
		return fmt.Errorf("encode output image %s: %w", outputPath, err)
	}

	return nil
}