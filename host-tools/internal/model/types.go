package model

type Point struct {
	X float64
	Y float64
}

type Path struct {
	Points []Point
	Closed bool
}

type MotionPrimitiveKind string

const (
	MotionPrimitiveTravel MotionPrimitiveKind = "travel"
	MotionPrimitiveDraw   MotionPrimitiveKind = "draw"
	MotionPrimitivePenUp  MotionPrimitiveKind = "pen_up"
	MotionPrimitivePenDown MotionPrimitiveKind = "pen_down"
)

type MotionPrimitive struct {
	Kind  MotionPrimitiveKind
	Point Point
	Feed  float64
	Meta  map[string]string
}

type PlannedSegment struct {
	Primitive MotionPrimitive
	DurationS float64
	EntryMMPS float64
	ExitMMPS  float64
}

type Command struct {
	Line string
	Meta map[string]string
}