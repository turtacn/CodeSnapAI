import pytest
from codesage.analyzers.go_parser import GoParser

@pytest.fixture
def go_parser():
    return GoParser()

@pytest.fixture
def sample_go_code():
    with open('tests/fixtures/sample.go', 'r') as f:
        return f.read()

def test_extract_functions_from_go(go_parser, sample_go_code):
    go_parser.parse(sample_go_code)
    functions = go_parser.extract_functions()
    assert len(functions) == 2
    assert functions[0].name == 'simpleFunc'
    assert functions[0].params == ['x int', 'y int']
    assert functions[1].name == 'complexFunc'

def test_calculate_complexity_go(go_parser):
    code = """
    func complexFunc(data []string) error {
        if len(data) == 0 {
            return fmt.Errorf("empty data")
        }
        for _, item := range data {
            switch item {
            case "a":
                fmt.Println("a")
            case "b":
                fmt.Println("b")
            default:
                fmt.Println("default")
            }
        }
        return nil
    }
    """
    go_parser.parse(code)
    functions = go_parser.extract_functions()
    assert functions[0].complexity >= 5

def test_extract_imports_go(go_parser, sample_go_code):
    go_parser.parse(sample_go_code)
    imports = go_parser.extract_imports()
    assert len(imports) == 3
    assert imports[0].path == 'encoding/json'
    assert imports[1].path == 'fmt'
    assert imports[2].path == 'net/http'

def test_extract_interface_go(go_parser, sample_go_code):
    go_parser.parse(sample_go_code)
    interfaces = go_parser.extract_interfaces()
    assert len(interfaces) == 1
    assert interfaces[0].name == 'Handler'
    assert len(interfaces[0].methods) == 1
    assert interfaces[0].methods[0].name == 'ServeHTTP'
