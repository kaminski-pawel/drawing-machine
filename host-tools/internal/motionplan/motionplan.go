package motionplan

import (
	"context"
	"fmt"

	"github.com/kaminski-pawel/drawing-machine/host-tools/internal/model"
)

type Planner interface {
	Plan(ctx context.Context, primitives []model.MotionPrimitive) ([]model.PlannedSegment, error)
}

type StubPlanner struct{}

func (StubPlanner) Plan(ctx context.Context, primitives []model.MotionPrimitive) ([]model.PlannedSegment, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if len(primitives) == 0 {
		return nil, fmt.Errorf("motion plan: no primitives provided")
	}

	return nil, fmt.Errorf("motion plan: trapezoidal planner not implemented yet")
}