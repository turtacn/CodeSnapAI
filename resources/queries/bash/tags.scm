(function_definition
    name: (word) @name
    body: (compound_statement) @body
) @func

(variable_assignment
    name: (variable_name) @name
    value: (_)? @value
) @assignment

(command
    name: (command_name (word) @cmd)
)
