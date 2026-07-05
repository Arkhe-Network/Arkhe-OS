use arkhe_unified_fs::*;

fn test_did() -> &'static str {
    "did:arkhe:test-user"
}

fn other_did() -> &'static str {
    "did:arkhe:other-user"
}

async fn setup_fs() -> UnifiedFileSystem {
    let fs = UnifiedFileSystem::new_memory(test_did());
    fs.init().await.unwrap();
    fs
}

#[tokio::test]
async fn init_creates_root() {
    let fs = setup_fs().await;
    assert!(fs.exists(&UnifiedPath::from_linux("/").unwrap()).await);
}

#[tokio::test]
async fn create_and_read_file() {
    let fs = setup_fs().await;
    let path = UnifiedPath::from_linux("/hello.txt").unwrap();

    fs.create_file(&path, test_did(), b"Hello, World!".to_vec())
        .await
        .unwrap();

    let content = fs.read_file(&path, test_did()).await.unwrap();
    assert_eq!(content, b"Hello, World!");
}

#[tokio::test]
async fn write_updates_content() {
    let fs = setup_fs().await;
    let path = UnifiedPath::from_linux("/file.txt").unwrap();

    fs.create_file(&path, test_did(), b"v1".to_vec()).await.unwrap();
    fs.write_file(&path, test_did(), b"v2".to_vec()).await.unwrap();

    let content = fs.read_file(&path, test_did()).await.unwrap();
    assert_eq!(content, b"v2");
}

#[tokio::test]
async fn create_directory_and_list() {
    let fs = setup_fs().await;
    let dir = UnifiedPath::from_linux("/docs").unwrap();
    let file = UnifiedPath::from_linux("/docs/readme.md").unwrap();

    fs.create_dir(&dir, test_did()).await.unwrap();
    fs.create_file(&file, test_did(), b"# Docs".to_vec()).await.unwrap();

    let entries = fs.readdir(&dir, test_did()).await.unwrap();
    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].0, "readme.md");
}

#[tokio::test]
async fn remove_file() {
    let fs = setup_fs().await;
    let path = UnifiedPath::from_linux("/temp.txt").unwrap();

    fs.create_file(&path, test_did(), b"temp".to_vec()).await.unwrap();
    assert!(fs.exists(&path).await);

    fs.remove_file(&path, test_did()).await.unwrap();
    assert!(!fs.exists(&path).await);
}

#[tokio::test]
async fn remove_dir_must_be_empty() {
    let fs = setup_fs().await;
    let dir = UnifiedPath::from_linux("/dir").unwrap();
    let file = UnifiedPath::from_linux("/dir/file.txt").unwrap();

    fs.create_dir(&dir, test_did()).await.unwrap();
    fs.create_file(&file, test_did(), b"x".to_vec()).await.unwrap();

    let result = fs.remove_dir(&dir, test_did()).await;
    assert!(result.is_err());
    assert!(result.unwrap_err().to_string().contains("not empty"));
}

#[tokio::test]
async fn stat_returns_meta() {
    let fs = setup_fs().await;
    let path = UnifiedPath::from_linux("/data.bin").unwrap();

    fs.create_file(&path, test_did(), vec![0u8; 1024]).await.unwrap();

    let meta = fs.stat(&path, test_did()).await.unwrap();
    assert_eq!(meta.size, 1024);
    assert_eq!(meta.owner_did, test_did());
    assert!(meta.integrity_hash.is_some());
}

#[tokio::test]
async fn owner_can_read_own_file() {
    let fs = setup_fs().await;
    let path = UnifiedPath::from_linux("/own.txt").unwrap();
    fs.create_file(&path, test_did(), b"mine".to_vec()).await.unwrap();

    // Owner deve conseguir ler
    assert!(fs.read_file(&path, test_did()).await.is_ok());
}

#[tokio::test]
async fn stranger_cannot_read_without_acl() {
    let fs = setup_fs().await;
    let path = UnifiedPath::from_linux("/secret.txt").unwrap();
    fs.create_file(&path, test_did(), b"secret".to_vec()).await.unwrap();

    // Outro DID sem ACL não deve conseguir ler
    let result = fs.read_file(&path, other_did()).await;
    assert!(result.is_err());
    let err = result.unwrap_err().to_string();
    assert!(err.contains("Permission denied"));
}

#[tokio::test]
async fn cannot_create_file_without_parent() {
    let fs = setup_fs().await;
    let path = UnifiedPath::from_linux("/nonexistent/file.txt").unwrap();

    let result = fs.create_file(&path, test_did(), b"x".to_vec()).await;
    assert!(result.is_err());
    assert!(result.unwrap_err().to_string().contains("not found"));
}

#[tokio::test]
async fn cannot_create_duplicate() {
    let fs = setup_fs().await;
    let path = UnifiedPath::from_linux("/dup.txt").unwrap();

    fs.create_file(&path, test_did(), b"first".to_vec()).await.unwrap();
    let result = fs.create_file(&path, test_did(), b"second".to_vec()).await;
    assert!(result.is_err());
    assert!(result.unwrap_err().to_string().contains("Already exists"));
}

#[tokio::test]
async fn read_nonexistent_fails() {
    let fs = setup_fs().await;
    let path = UnifiedPath::from_linux("/nope.txt").unwrap();

    let result = fs.read_file(&path, test_did()).await;
    assert!(result.is_err());
    assert!(result.unwrap_err().to_string().contains("not found"));
}

#[tokio::test]
async fn audit_callback_receives_events() {
    use std::sync::Mutex;

    let events: Arc<Mutex<Vec<AuditEvent>>> = Arc::new(Mutex::new(Vec::new()));
    let events_clone = Arc::clone(&events);

    let fs = UnifiedFileSystem::new_memory(test_did())
        .with_audit(Box::new(move |event| {
            events_clone.lock().unwrap().push(event);
        }));

    fs.init().await.unwrap();

    let path = UnifiedPath::from_linux("/audited.txt").unwrap();
    fs.create_file(&path, test_did(), b"audit me".to_vec())
        .await
        .unwrap();

    let events = events.lock().unwrap();
    assert!(events.len() >= 1);
    assert_eq!(events[0].action, "create_file");
    assert_eq!(events[0].subject_did, test_did());
    assert!(events[0].success);
}

#[tokio::test]
async fn windows_path_works() {
    let fs = setup_fs().await;

    // Criar via caminho Windows
    let win_path = UnifiedPath::from_windows(r"C:\Users\test\file.txt").unwrap();
    let parent = win_path.parent().unwrap();

    fs.create_dir(&parent, test_did()).await.unwrap();
    fs.create_file(&win_path, test_did(), b"windows content".to_vec())
        .await
        .unwrap();

    // Ler via caminho Linux (mesma estrutura interna)
    let linux_path = UnifiedPath::from_linux("/Users/test/file.txt").unwrap();
    let content = fs.read_file(&linux_path, test_did()).await.unwrap();
    assert_eq!(content, b"windows content");
}

#[tokio::test]
async fn nested_directories() {
    let fs = setup_fs().await;

    let a = UnifiedPath::from_linux("/a").unwrap();
    let b = UnifiedPath::from_linux("/a/b").unwrap();
    let c = UnifiedPath::from_linux("/a/b/c").unwrap();
    let file = UnifiedPath::from_linux("/a/b/c/deep.txt").unwrap();

    fs.create_dir(&a, test_did()).await.unwrap();
    fs.create_dir(&b, test_did()).await.unwrap();
    fs.create_dir(&c, test_did()).await.unwrap();
    fs.create_file(&file, test_did(), b"deep".to_vec()).await.unwrap();

    let entries = fs.readdir(&c, test_did()).await.unwrap();
    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].0, "deep.txt");
}

#[tokio::test]
async fn rename_file() {
    let fs = setup_fs().await;

    let from = UnifiedPath::from_linux("/old.txt").unwrap();
    let to = UnifiedPath::from_linux("/new.txt").unwrap();

    fs.create_file(&from, test_did(), b"content".to_vec()).await.unwrap();
    fs.backend.rename(&from, &to).await.unwrap();

    assert!(!fs.exists(&from).await);
    assert!(fs.exists(&to).await);

    let content = fs.read_file(&to, test_did()).await.unwrap();
    assert_eq!(content, b"content");
}
