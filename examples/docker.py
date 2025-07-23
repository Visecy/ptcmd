from prompt_toolkit.shortcuts import CompleteStyle
from ptcmd import auto_argument, Arg, Cmd

class DockerApp(Cmd):
    DEFAULT_PROMPT = "[cmd.prompt]docker[/cmd.prompt]> "
    DEFAULT_COMPLETE_STYLE = CompleteStyle.MULTI_COLUMN

    @auto_argument
    def do_run(self, image: Arg[str, "-i", "--image", {"help": "Docker image to run"}]) -> None:  # noqa: F821,B002,F722
        """Run a Docker container"""
        self.poutput(f"Running Docker container with image: {image}")

    @auto_argument
    def do_ps(self) -> None:
        """List running Docker containers"""
        self.poutput("Listing running Docker containers...")

    @auto_argument
    def do_pull(self, image: Arg[str, "-i", "--image", {"help": "Docker image to pull"}]) -> None:  # noqa: F821,B002,F722
        """Pull a Docker image"""
        self.poutput(f"Pulling Docker image: {image}")

    @auto_argument
    def do_stop(self, container_id: Arg[str, "-c", "--container", {"help": "Container ID to stop"}]) -> None:  # noqa: F821,B002,F722
        """Stop a running Docker container"""
        self.poutput(f"Stopping Docker container with ID: {container_id}")

    @auto_argument
    def do_rm(self, container_id: Arg[str, "-c", "--container", {"help": "Container ID to remove"}]) -> None:  # noqa: F821,B002,F722
        """Remove a Docker container"""
        self.poutput(f"Removing Docker container with ID: {container_id}")

    @auto_argument
    def do_compose(self) -> None:
        """Run Docker Compose commands"""
        self.poutput("Running Docker Compose commands...")
    
    @do_compose.add_subcommand("up")
    def compose_up(self) -> None:
        """Start services defined in docker-compose.yml"""
        self.poutput("Starting services with Docker Compose...")
    
    @do_compose.add_subcommand("down")
    def compose_down(self) -> None:
        """Stop services defined in docker-compose.yml"""
        self.poutput("Stopping services with Docker Compose...")


if __name__ == "__main__":
    DockerApp().cmdloop()
