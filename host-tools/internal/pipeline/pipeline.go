package pipeline

import (
	"context"
	"fmt"

	"github.com/kaminski-pawel/drawing-machine/host-tools/internal/config"
	"github.com/kaminski-pawel/drawing-machine/host-tools/internal/gcodeout"
	"github.com/kaminski-pawel/drawing-machine/host-tools/internal/imageprep"
	"github.com/kaminski-pawel/drawing-machine/host-tools/internal/motionplan"
	"github.com/kaminski-pawel/drawing-machine/host-tools/internal/svgopt"
	"github.com/kaminski-pawel/drawing-machine/host-tools/internal/vectorize"
)

type Runner struct {
	Specs      config.Specs
	ImagePrep  imageprep.Preparer
	Vectorize  vectorize.Vectorizer
	SVGOpt     svgopt.Optimizer
	MotionPlan motionplan.Planner
	GCodeOut   gcodeout.Encoder
}

type PrepareRequest struct {
	InputPath string
	Options   imageprep.Options
}

func NewRunner(specs config.Specs) Runner {
	return Runner{
		Specs:      specs,
		ImagePrep:  imageprep.NewService(),
		Vectorize:  vectorize.Stub{},
		SVGOpt:     svgopt.NoopOptimizer{},
		MotionPlan: motionplan.StubPlanner{},
		GCodeOut:   gcodeout.StubEncoder{},
	}
}

func (r Runner) Prepare(ctx context.Context, request PrepareRequest) (*imageprep.PreparedImage, error) {
	if r.ImagePrep == nil {
		return nil, fmt.Errorf("prepare image %s: image preparation stage is not configured", request.InputPath)
	}

	prepared, err := r.ImagePrep.PrepareFile(ctx, request.InputPath, request.Options)
	if err != nil {
		return nil, err
	}

	return prepared, nil
}