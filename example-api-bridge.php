<?php
// api-bridge.php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, X-API-Key');

$VALID_API_KEY = getenv('BRIDGE_API_KEY') ?: 'astral-ai-secret-key-2024';
// If you prefer constant: $VALID_API_KEY = 'your_real_key_here';

// Accept options (CORS preflight)
if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
    exit(0);
}

// Read API key
$api_key = $_SERVER['HTTP_X_API_KEY'] ?? '';
if ($api_key !== $VALID_API_KEY) {
    http_response_code(401);
    echo json_encode(["success" => false, "error" => "Invalid API key"]);
    exit;
}

// Input payload (bridge expects JSON body)
$input = json_decode(file_get_contents('php://input'), true) ?: [];

// Determine action
$action = $_GET['action'] ?? 'test';

// Decide driver based on payload.system_type or default to mysql
$system_type = strtolower($input['system_type'] ?? 'mysql');

try {
    // If bridge is used as single-hosted for a fixed DB on that server,
    // you may want to ignore passed credentials and use local config.
    // But we'll support both modes: if db_username provided in payload, use payload.
    if ($system_type === 'postgres' || $system_type === 'postgresql') {
        // Postgres (PDO pgsql)
        $db_host = $input['db_host'] ?? '127.0.0.1';
        $db_port = $input['db_port'] ?? 5432;
        $db_name = $input['db_name'] ?? '';
        $db_user = $input['db_username'] ?? '';
        $db_pass = $input['db_password'] ?? '';
        $dsn = "pgsql:host={$db_host};port={$db_port};dbname={$db_name}";
    } else {
        // MySQL (PDO mysql)
        $db_host = $input['db_host'] ?? 'localhost';
        $db_port = $input['db_port'] ?? 3306;
        $db_name = $input['db_name'] ?? '';
        $db_user = $input['db_username'] ?? '';
        $db_pass = $input['db_password'] ?? '';
        $dsn = "mysql:host={$db_host};port={$db_port};dbname={$db_name};charset=utf8mb4";
    }

    // Prepare PDO
    $pdo = new PDO($dsn, $db_user, $db_pass, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);

    switch ($action) {
        case 'test':
            // simple test
            if ($system_type === 'postgres' || $system_type === 'postgresql') {
                $stmt = $pdo->query("SELECT 1 as connection_test, NOW() as server_time");
            } else {
                $stmt = $pdo->query("SELECT 1 as connection_test, NOW() as server_time");
            }
            $row = $stmt->fetch(PDO::FETCH_ASSOC);

            // get table count
            if ($system_type === 'postgres' || $system_type === 'postgresql') {
                $stmt = $pdo->query("SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public' AND table_type='BASE TABLE'");
                $tc = $stmt->fetch(PDO::FETCH_ASSOC);
            } else {
                $stmt = $pdo->query("SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = DATABASE()");
                $tc = $stmt->fetch(PDO::FETCH_ASSOC);
            }

            echo json_encode([
                "success" => true,
                "message" => "Bridge connected successfully",
                "data" => [
                    "connection_test" => $row['connection_test'] ?? null,
                    "server_time" => $row['server_time'] ?? null,
                    "table_count" => $tc['table_count'] ?? 0,
                    "connection_type" => ($system_type === 'postgres' ? 'pgsql' : 'mysql')
                ]
            ]);
            break;

        case 'schema':
            $schema = [];

            if ($system_type === 'postgres' || $system_type === 'postgresql') {
                $stmt = $pdo->query("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'");
                $tables = $stmt->fetchAll(PDO::FETCH_ASSOC);
                foreach ($tables as $t) {
                    $table_name = $t['table_name'];
                    $cstmt = $pdo->prepare("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = :t");
                    $cstmt->execute([':t'=>$table_name]);
                    $cols = $cstmt->fetchAll(PDO::FETCH_ASSOC);
                    $schema[$table_name] = [
                        "columns" => array_column($cols, 'column_name'),
                        "column_details" => $cols
                    ];
                }
            } else {
                $stmt = $pdo->query("SELECT TABLE_NAME as table_name FROM information_schema.tables WHERE table_schema = DATABASE()");
                $tables = $stmt->fetchAll(PDO::FETCH_ASSOC);
                foreach ($tables as $t) {
                    $table_name = $t['table_name'];
                    $cstmt = $pdo->query("DESCRIBE `{$table_name}`");
                    $cols = $cstmt->fetchAll(PDO::FETCH_ASSOC);
                    $schema[$table_name] = [
                        "columns" => array_column($cols, 'Field'),
                        "column_details" => $cols
                    ];
                }
            }

            echo json_encode([
                "success" => true,
                "schema" => $schema,
                "table_count" => count($schema)
            ]);
            break;

        case 'execute':
            $query = trim($input['query'] ?? '');
            if (empty($query)) {
                echo json_encode(["success" => false, "error" => "No query provided"]);
                break;
            }
            // Security: only allow SELECT
            if (stripos($query, 'SELECT') !== 0) {
                echo json_encode(["success" => false, "error" => "Only SELECT queries are allowed"]);
                break;
            }

            $stmt = $pdo->query($query);
            $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
            echo json_encode([
                "success" => true,
                "data" => $rows,
                "row_count" => count($rows)
            ]);
            break;

        default:
            echo json_encode(["success" => false, "error" => "Invalid action"]);
            break;
    }

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(["success" => false, "error" => $e->getMessage()]);
    exit;
}
