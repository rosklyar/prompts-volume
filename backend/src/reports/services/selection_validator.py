"""Service for validating user's evaluation selections."""

from dataclasses import dataclass

from src.reports.models.api_models import PromptSelection, PromptSelectionInfo


@dataclass
class ValidationResult:
    """Result of selection validation."""

    is_valid: bool
    errors: list[str]
    # Normalized selections with defaults filled in
    normalized_selections: list[PromptSelection] | None


class SelectionValidatorService:
    """Validates user's evaluation selections for report generation."""

    def validate_selections(
        self,
        selections: list[PromptSelection],
        prompt_selection_info: list[PromptSelectionInfo],
        use_defaults_for_unspecified: bool,
    ) -> ValidationResult:
        """Validate user's selections against available options.

        Validates:
        1. All prompt_ids in selections belong to the group
        2. All evaluation_ids are valid for their prompts (in available_options)
        3. No duplicate prompt_ids

        If use_defaults_for_unspecified is True, fills in defaults for
        prompts not in the selections list.

        Returns ValidationResult with normalized selections.
        """
        errors: list[str] = []

        # Build maps for quick lookup
        prompt_info_map = {info.prompt_id: info for info in prompt_selection_info}
        valid_prompt_ids = set(prompt_info_map.keys())

        # Build map of valid evaluation_ids per prompt
        valid_eval_ids_per_prompt: dict[int, set[int]] = {}
        for info in prompt_selection_info:
            valid_eval_ids_per_prompt[info.prompt_id] = {
                opt.evaluation_id for opt in info.available_options
            }

        # Check for duplicate prompt_ids
        seen_prompt_ids: set[int] = set()
        for selection in selections:
            if selection.prompt_id in seen_prompt_ids:
                errors.append(
                    f"Duplicate prompt_id in selections: {selection.prompt_id}"
                )
            seen_prompt_ids.add(selection.prompt_id)

        # Validate each selection
        for selection in selections:
            # Check prompt belongs to group
            if selection.prompt_id not in valid_prompt_ids:
                errors.append(
                    f"prompt_id {selection.prompt_id} does not belong to this group"
                )
                continue

            # If evaluation_id is provided, validate it's in available options
            if selection.evaluation_id is not None:
                valid_evals = valid_eval_ids_per_prompt.get(selection.prompt_id, set())
                if selection.evaluation_id not in valid_evals:
                    errors.append(
                        f"evaluation_id {selection.evaluation_id} is not a valid "
                        f"completed evaluation for prompt_id {selection.prompt_id}"
                    )

        if errors:
            return ValidationResult(
                is_valid=False,
                errors=errors,
                normalized_selections=None,
            )

        # Build normalized selections
        selections_map = {s.prompt_id: s for s in selections}
        normalized: list[PromptSelection] = []

        for prompt_id in valid_prompt_ids:
            if prompt_id in selections_map:
                # Use user's selection
                normalized.append(selections_map[prompt_id])
            elif use_defaults_for_unspecified:
                # Use default selection
                info = prompt_info_map[prompt_id]
                normalized.append(
                    PromptSelection(
                        prompt_id=prompt_id,
                        evaluation_id=info.default_selection,
                    )
                )
            else:
                # Mark as awaiting (no evaluation selected)
                normalized.append(
                    PromptSelection(
                        prompt_id=prompt_id,
                        evaluation_id=None,
                    )
                )

        return ValidationResult(
            is_valid=True,
            errors=[],
            normalized_selections=normalized,
        )
