class Pipeline:
    """
    Manages the sequential execution of steps in the shorts-factory pipeline.
    This class defines the DAG (Directed Acyclic Graph) of steps and provides
    logic to determine which steps are runnable based on the current job state.
    """

    STEPS = [
        "idea_gen",
        "tts",
        "bgm_mix",
        "scenes",
        "clips",
        "render",
        "thumbnail",
        "upload_yt"
    ]

    def get_runnable_steps(self, completed_steps: set[str]) -> list[str]:
        """
        Determines which steps are currently runnable based on completed steps.
        
        A step is runnable if all its predecessors in the STEPS list are completed.
        Since this is a linear DAG, it returns a list containing the first 
        incomplete step, or an empty list if all steps are done.

        Args:
            completed_steps: A set of step names that have been successfully finished.

        Returns:
            A list containing at most one runnable step name.
        """
        for step in self.STEPS:
            if step not in completed_steps:
                return [step]
        return []

    def is_complete(self, completed_steps: set[str]) -> bool:
        """
        Checks if all steps in the pipeline have been completed.

        Args:
            completed_steps: A set of step names that have been successfully finished.

        Returns:
            True if all required steps are in completed_steps, False otherwise.
        """
        return all(step in completed_steps for step in self.STEPS)
