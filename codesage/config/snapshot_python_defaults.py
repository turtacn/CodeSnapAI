from pydantic import BaseModel, Field


class PythonSnapshotConfig(BaseModel):
    include_tests: bool = Field(True, description="Whether to include test files in the snapshot.")
    aggregate_by_module: bool = Field(False, description="Whether to aggregate snapshot data by module instead of by file.")
    generate_compat_modules_view: bool = Field(True, description="Whether to generate a simplified 'modules' view for backward compatibility.")
