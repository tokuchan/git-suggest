# Functional programming style: small composable functions, curried over manager objects

Code is written as small, single-purpose functions composed into larger
behavior, rather than stateful "manager" classes. Where parameterized
behavior is needed, prefer curried functions (e.g. a function returning a
function) over an object with configuration held in instance state. Objects
are permitted but stay data-focused (plain data containers, e.g. pydantic
models) with short methods; they are not used to hold behavior-heavy,
mutable "service" state.
