export const translations = {
  en: {
    appSubtitle: "Intelligent Automated Network Training Laboratory",

    navHome: "Home",
    navCreateLab: "Create Lab",
    navSessionDetail: "Session Detail",
    navValidationResult: "Validation Result",

    language: "Language",
    english: "EN",
    turkish: "TR",

    dashboardTitle: "AutoNetLab Dashboard",
    dashboardDescription:
      "This dashboard helps students create virtual network labs, view lab session information, inspect topology details, run validation, and receive learning recommendations.",
    createNewLab: "Create New Lab",
    viewCurrentLab: "View Current Lab",

    loadingLabDataTitle: "Loading lab data",
    loadingLabDataMessage:
      "The dashboard is loading the current mock lab session information.",

    currentLab: "Current Lab",
    difficulty: "Difficulty",
    status: "Status",
    injectedErrors: "Injected Errors",
    activeLabSessionIdentifier: "Active lab session identifier",
    selectedLabDifficultyLevel: "Selected lab difficulty level",
    currentLabSessionStatus: "Current lab session status",
    numberOfGeneratedErrors: "Number of generated troubleshooting errors",

    createLabTitle: "Create Lab",
    createLabDescription:
      "Select a difficulty level. This value will be sent to the backend as easy, medium, or hard.",
    studentId: "Student ID",
    topologyTemplate: "Topology Template",
    createLabButton: "Create Lab",
    creating: "Creating...",
    difficultyPreview: "Difficulty Preview",
    backendValue: "Backend Value",
    labCreationFailed: "Lab creation failed",
    labCreationFailedMessage:
      "Lab session could not be created. Please try again.",
    difficultyOptionsFailed:
      "Difficulty options could not be loaded.",
    createLabNote:
      "Create a new troubleshooting lab session and continue from the workspace.",
    difficultyLoading: "Difficulty description is loading...",
    easyCreates: "Easy creates 2 injected errors.",
    mediumCreates: "Medium creates 3 injected errors.",
    hardCreates: "Hard creates 5 injected errors.",

    labSessionDetail: "Lab Session Detail",
    labSessionLoading: "Lab session data is loading...",
    sessionId: "Session ID",
    student: "Student",
    nodes: "Nodes",
    links: "Links",
    cliAccess: "CLI Access",
    validateLab: "Validate Lab",
    backendFormatNote:
      "This screen now follows the backend lab session response format.",
    topology: "Topology",
    topologyLoading: "Topology data is loading...",
    topologyName: "Topology Name",
    managementIpv4: "Management IPv4",
    notAssignedYet: "Not assigned yet",
    id: "ID",
    kind: "Kind",
    image: "Image",
    topic: "Topic",
    device: "Device",
    severity: "Severity",

    validationResultTitle: "Validation Result",
    validationResultDescription:
      "Run validation to check whether the current network configuration satisfies the expected topology state. The response format now follows the backend ValidationResult schema.",
    runValidation: "Run Validation",
    validating: "Validating...",
    validationRunningTitle: "Validation is running",
    validationRunningMessage:
      "The system is checking the current lab session. Please wait...",
    noValidationTitle: "No validation result yet",
    noValidationMessage:
      "Click the Run Validation button to generate PASS/FAIL checks and a score.",
    validationSummary: "Validation Summary",
    allChecksPassed: "All validation checks passed successfully.",
    someChecksFailed:
      "Some validation checks failed. Review the failed topics below.",
    totalChecks: "Total Checks",
    passedChecks: "Passed Checks",
    failedChecks: "Failed Checks",
    checkDetails: "Check Details",
    checkId: "Check ID",
    somethingWentWrong: "Something went wrong",
    noActiveLab:
      "There is no active lab session to validate.",
    validationFailed:
      "Validation failed. Please try again.",

    recommendation: "Recommendation",
    recommendationEmpty:
      "Recommendations will appear after validation if any topic needs review.",
    recommendationNumber: "Recommendation",

    easy: "Easy",
    medium: "Medium",
    hard: "Hard",

    created: "Created",
    deployed: "Deployed",
    destroyed: "Destroyed",
    validated: "Validated",
    error: "Error"
  },

  tr: {
    appSubtitle: "Akıllı Otomatik Ağ Eğitim Laboratuvarı",

    navHome: "Ana Sayfa",
    navCreateLab: "Lab Oluştur",
    navSessionDetail: "Oturum Detayı",
    navValidationResult: "Doğrulama Sonucu",

    language: "Dil",
    english: "EN",
    turkish: "TR",

    dashboardTitle: "AutoNetLab Paneli",
    dashboardDescription:
      "Bu panel öğrencilerin sanal ağ laboratuvarları oluşturmasını, lab oturum bilgilerini görüntülemesini, topoloji detaylarını incelemesini, doğrulama çalıştırmasını ve öğrenme önerileri almasını sağlar.",
    createNewLab: "Yeni Lab Oluştur",
    viewCurrentLab: "Mevcut Labı Görüntüle",

    loadingLabDataTitle: "Lab verisi yükleniyor",
    loadingLabDataMessage:
      "Panel mevcut mock lab oturumu bilgisini yüklüyor.",

    currentLab: "Mevcut Lab",
    difficulty: "Zorluk",
    status: "Durum",
    injectedErrors: "Eklenen Hatalar",
    activeLabSessionIdentifier: "Aktif lab oturum kimliği",
    selectedLabDifficultyLevel: "Seçilen lab zorluk seviyesi",
    currentLabSessionStatus: "Mevcut lab oturum durumu",
    numberOfGeneratedErrors: "Üretilen hata sayısı",

    createLabTitle: "Lab Oluştur",
    createLabDescription:
      "Bir zorluk seviyesi seç. Bu değer backend tarafına easy, medium veya hard olarak gönderilir.",
    studentId: "Öğrenci ID",
    topologyTemplate: "Topoloji Şablonu",
    createLabButton: "Lab Oluştur",
    creating: "Oluşturuluyor...",
    difficultyPreview: "Zorluk Önizlemesi",
    backendValue: "Backend Değeri",
    labCreationFailed: "Lab oluşturma başarısız",
    labCreationFailedMessage:
      "Lab oturumu oluşturulamadı. Lütfen tekrar dene.",
    difficultyOptionsFailed:
      "Zorluk seçenekleri yüklenemedi.",
    createLabNote:
      "Not: Bu sayfa şu anda backend uyumlu mock veri kullanıyor. Daha sonra POST /api/labs çağrısı yapacak.",
    difficultyLoading: "Zorluk açıklaması yükleniyor...",
    easyCreates: "Kolay seviye 2 hata üretir.",
    mediumCreates: "Orta seviye 3 hata üretir.",
    hardCreates: "Zor seviye 5 hata üretir.",

    labSessionDetail: "Lab Oturum Detayı",
    labSessionLoading: "Lab oturum verisi yükleniyor...",
    sessionId: "Oturum ID",
    student: "Öğrenci",
    nodes: "Düğümler",
    links: "Bağlantılar",
    cliAccess: "CLI Erişimi",
    validateLab: "Labı Doğrula",
    backendFormatNote:
      "Bu ekran artık backend lab session response formatını takip ediyor.",
    topology: "Topoloji",
    topologyLoading: "Topoloji verisi yükleniyor...",
    topologyName: "Topoloji Adı",
    managementIpv4: "Yönetim IPv4",
    notAssignedYet: "Henüz atanmadı",
    id: "ID",
    kind: "Tür",
    image: "İmaj",
    topic: "Konu",
    device: "Cihaz",
    severity: "Önem Seviyesi",

    validationResultTitle: "Doğrulama Sonucu",
    validationResultDescription:
      "Mevcut ağ yapılandırmasının beklenen topoloji durumunu karşılayıp karşılamadığını kontrol etmek için doğrulama çalıştır. Response formatı artık backend ValidationResult şemasını takip ediyor.",
    runValidation: "Doğrulamayı Çalıştır",
    validating: "Doğrulanıyor...",
    validationRunningTitle: "Doğrulama çalışıyor",
    validationRunningMessage:
      "Sistem mevcut lab oturumunu kontrol ediyor. Lütfen bekle...",
    noValidationTitle: "Henüz doğrulama sonucu yok",
    noValidationMessage:
      "PASS/FAIL kontrollerini ve puanı üretmek için Doğrulamayı Çalıştır butonuna bas.",
    validationSummary: "Doğrulama Özeti",
    allChecksPassed: "Tüm doğrulama kontrolleri başarıyla geçti.",
    someChecksFailed:
      "Bazı doğrulama kontrolleri başarısız oldu. Aşağıdaki konuları incele.",
    totalChecks: "Toplam Kontrol",
    passedChecks: "Geçen Kontrol",
    failedChecks: "Başarısız Kontrol",
    checkDetails: "Kontrol Detayları",
    checkId: "Kontrol ID",
    somethingWentWrong: "Bir şeyler ters gitti",
    noActiveLab:
      "Doğrulanacak aktif bir lab oturumu yok.",
    validationFailed:
      "Doğrulama başarısız oldu. Lütfen tekrar dene.",

    recommendation: "Öneri",
    recommendationEmpty:
      "İncelenmesi gereken konu varsa öneriler doğrulamadan sonra burada görünecek.",
    recommendationNumber: "Öneri",

    easy: "Kolay",
    medium: "Orta",
    hard: "Zor",

    created: "Oluşturuldu",
    deployed: "Dağıtıldı",
    destroyed: "Kapatıldı",
    validated: "Doğrulandı",
    error: "Hata"
  }
};