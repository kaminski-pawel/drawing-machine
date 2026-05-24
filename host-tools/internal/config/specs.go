package config

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

const specsFileName = "specs.yml"

type Specs struct {
	Project Project `yaml:"project"`
	Machine *Machine `yaml:"machine,omitempty"`
}

type Project struct {
	Name        string `yaml:"name"`
	Description string `yaml:"description"`
}

type Machine struct {
	Workspace *Workspace `yaml:"workspace,omitempty"`
	Motion    *Motion    `yaml:"motion,omitempty"`
}

type Workspace struct {
	WidthMM  float64 `yaml:"width_mm"`
	HeightMM float64 `yaml:"height_mm"`
	Origin   string  `yaml:"origin"`
}

type Motion struct {
	Units             string  `yaml:"units"`
	MaxFeedMMPerMin   float64 `yaml:"max_feed_mm_per_min"`
	MaxAccelMMPerS2   float64 `yaml:"max_accel_mm_per_s2"`
	JerkPolicy        string  `yaml:"jerk_policy"`
	LeftStepsPerMM    float64 `yaml:"left_steps_per_mm"`
	RightStepsPerMM   float64 `yaml:"right_steps_per_mm"`
	PenUpDelayMS      int     `yaml:"pen_up_delay_ms"`
	PenDownDelayMS    int     `yaml:"pen_down_delay_ms"`
	DefaultFeedMMMin  float64 `yaml:"default_feed_mm_per_min"`
	TravelFeedMMMin   float64 `yaml:"travel_feed_mm_per_min"`
}

func LoadSpecs(path string) (Specs, error) {
	content, err := os.ReadFile(path)
	if err != nil {
		return Specs{}, fmt.Errorf("read specs %s: %w", path, err)
	}

	var specs Specs
	if err := yaml.Unmarshal(content, &specs); err != nil {
		return Specs{}, fmt.Errorf("parse specs %s: %w", path, err)
	}
	if specs.Project.Name == "" {
		return Specs{}, fmt.Errorf("parse specs %s: missing project.name", path)
	}

	return specs, nil
}

func FindDefaultSpecsPath() (string, error) {
	startDir, err := os.Getwd()
	if err != nil {
		return "", fmt.Errorf("get working directory: %w", err)
	}

	root, err := FindRepoRoot(startDir)
	if err != nil {
		return "", err
	}

	return filepath.Join(root, specsFileName), nil
}

func FindRepoRoot(startDir string) (string, error) {
	current := filepath.Clean(startDir)

	for {
		candidate := filepath.Join(current, specsFileName)
		if _, err := os.Stat(candidate); err == nil {
			return current, nil
		} else if !os.IsNotExist(err) {
			return "", fmt.Errorf("stat %s: %w", candidate, err)
		}

		parent := filepath.Dir(current)
		if parent == current {
			return "", fmt.Errorf("could not find %s above %s", specsFileName, startDir)
		}
		current = parent
	}
}