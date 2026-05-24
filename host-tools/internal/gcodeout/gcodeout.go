package gcodeout

import (
	"context"
	"fmt"

	"github.com/kaminski-pawel/drawing-machine/host-tools/internal/model"
)

type Encoder interface {
	Encode(ctx context.Context, segments []model.PlannedSegment) ([]model.Command, error)
}

type StubEncoder struct{}

func (StubEncoder) Encode(ctx context.Context, segments []model.PlannedSegment) ([]model.Command, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if len(segments) == 0 {
		return nil, fmt.Errorf("gcode encode: no planned segments provided")
	}

	return nil, fmt.Errorf("gcode encode: command generator not implemented yet")
}