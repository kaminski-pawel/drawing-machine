package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"os"

	"github.com/kaminski-pawel/drawing-machine/host-tools/internal/config"
	"github.com/kaminski-pawel/drawing-machine/host-tools/internal/imageprep"
	"github.com/kaminski-pawel/drawing-machine/host-tools/internal/pipeline"
)

func main() {
	if err := run(context.Background(), os.Args[1:]); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(1)
	}
}

func run(ctx context.Context, args []string) error {
	if len(args) == 0 {
		printUsage(os.Stdout)
		return nil
	}

	defaultSpecsPath, err := config.FindDefaultSpecsPath()
	if err != nil {
		defaultSpecsPath = "specs.yml"
	}

	switch args[0] {
	case "prepare":
		return runPrepare(ctx, defaultSpecsPath, args[1:])
	case "inspect-specs":
		return runInspectSpecs(defaultSpecsPath, args[1:])
	case "help", "-h", "--help":
		printUsage(os.Stdout)
		return nil
	default:
		printUsage(os.Stderr)
		return fmt.Errorf("unknown subcommand %q", args[0])
	}
}

func runPrepare(ctx context.Context, defaultSpecsPath string, args []string) error {
	fs := flag.NewFlagSet("prepare", flag.ContinueOnError)
	fs.SetOutput(os.Stderr)

	inputPath := fs.String("input", "", "input PNG or JPEG image")
	outputPath := fs.String("output", "", "output PNG path for normalized grayscale bitmap")
	specsPath := fs.String("specs", defaultSpecsPath, "path to repository specs.yml")
	threshold := fs.Int("threshold", -1, "optional threshold in range 0-255; negative disables thresholding")

	if err := fs.Parse(args); err != nil {
		return err
	}
	if *inputPath == "" || *outputPath == "" {
		return errors.New("prepare requires -input and -output")
	}
	if *threshold > 255 {
		return fmt.Errorf("threshold %d exceeds maximum value 255", *threshold)
	}

	specs, err := config.LoadSpecs(*specsPath)
	if err != nil {
		return err
	}

	runner := pipeline.NewRunner(specs)
	prepared, err := runner.Prepare(ctx, pipeline.PrepareRequest{
		InputPath: *inputPath,
		Options: imageprep.Options{
			Threshold: *threshold,
		},
	})
	if err != nil {
		return err
	}

	if err := imageprep.WritePNG(*outputPath, prepared.Bitmap); err != nil {
		return err
	}

	fmt.Fprintf(os.Stdout, "prepared %s -> %s (%dx%d)\n", *inputPath, *outputPath, prepared.Bitmap.Bounds().Dx(), prepared.Bitmap.Bounds().Dy())
	return nil
}

func runInspectSpecs(defaultSpecsPath string, args []string) error {
	fs := flag.NewFlagSet("inspect-specs", flag.ContinueOnError)
	fs.SetOutput(os.Stderr)

	specsPath := fs.String("specs", defaultSpecsPath, "path to repository specs.yml")
	if err := fs.Parse(args); err != nil {
		return err
	}

	specs, err := config.LoadSpecs(*specsPath)
	if err != nil {
		return err
	}

	if specs.Machine == nil || specs.Machine.Motion == nil {
		fmt.Fprintf(os.Stdout, "%s: machine motion limits are not defined in %s yet\n", specs.Project.Name, *specsPath)
		return nil
	}

	fmt.Fprintf(
		os.Stdout,
		"%s: units=%s max_feed_mm_per_min=%.2f max_accel_mm_per_s2=%.2f jerk_policy=%s\n",
		specs.Project.Name,
		specs.Machine.Motion.Units,
		specs.Machine.Motion.MaxFeedMMPerMin,
		specs.Machine.Motion.MaxAccelMMPerS2,
		specs.Machine.Motion.JerkPolicy,
	)
	return nil
}

func printUsage(output *os.File) {
	fmt.Fprintln(output, "pipeline: host-side image transformation scaffold")
	fmt.Fprintln(output, "")
	fmt.Fprintln(output, "Usage:")
	fmt.Fprintln(output, "  pipeline prepare -input input.png -output prepared.png [-specs path] [-threshold 128]")
	fmt.Fprintln(output, "  pipeline inspect-specs [-specs path]")
}