package vectorize

import (
	"context"
	"fmt"
	"image"

	"github.com/kaminski-pawel/drawing-machine/host-tools/internal/model"
)

type Vectorizer interface {
	Trace(ctx context.Context, bitmap *image.Gray) ([]model.Path, error)
}

type Stub struct{}

func (Stub) Trace(ctx context.Context, bitmap *image.Gray) ([]model.Path, error) {
	if err := ctx.Err(); err != nil {
		return nil, fmt.Errorf("vectorize bitmap: %w", err)
	}
	if bitmap == nil {
		return nil, fmt.Errorf("vectorize bitmap: nil bitmap")
	}

	return nil, fmt.Errorf("vectorize bitmap: not implemented; plug in a Potrace-backed vectorizer")
}