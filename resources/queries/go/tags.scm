(function_declaration
    name: (identifier) @name) @func

(method_declaration
    receiver: (parameter_list) @receiver
    name: (field_identifier) @name) @method

(type_declaration
    (type_spec
        name: (type_identifier) @name
        type: (struct_type) @struct_body
    ) @type_spec
)

(type_declaration
    (type_spec
        name: (type_identifier) @name
        type: (interface_type) @interface_body
    ) @type_spec
)

(import_spec
    name: (package_identifier)? @alias
    path: (interpreted_string_literal) @path
) @import

(go_statement) @go

(send_statement) @send
(unary_expression operator: "<-") @recv
(channel_type) @chan_type

(if_statement
    condition: (binary_expression
        left: (identifier) @left
        operator: "!="
        right: (nil)
    )
) @if_err
(#eq? @left "err")
