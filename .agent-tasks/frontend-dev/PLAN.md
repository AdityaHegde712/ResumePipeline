# Frontend Plan: Common UI Components

## Objective
Build 6 reusable React components for the resume pipeline frontend.

## Components

| # | Component | Purpose |
|---|-----------|---------|
| 1 | `LoadingSpinner` | Centered spinner with optional message |
| 2 | `EmptyState` | Placeholder for empty data states |
| 3 | `ErrorState` | Styled error banner with retry |
| 4 | `ConfirmDialog` | Modal confirmation dialog |
| 5 | `TagInput` | Chip-style tag input with Enter-to-add |
| 6 | `StatusBadge` | Color-coded pipeline status indicator |

## Approach
- React 19 + TypeScript + CSS Modules
- Use existing CSS variables from `variables.css`
- Components live in `src/components/common/`
- Each component gets a `.tsx` and `.module.css` file
