package svgopt

import (
	"context"

	"github.com/kaminski-pawel/drawing-machine/host-tools/internal/model"
)

type Optimizer interface {
	Optimize(ctx context.Context, paths []model.Path) ([]model.Path, error)
}

type NoopOptimizer struct{}

func (NoopOptimizer) Optimize(ctx context.Context, paths []model.Path) ([]model.Path, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	cloned := make([]model.Path, len(paths))
	copy(cloned, paths)
	return cloned, nil
}