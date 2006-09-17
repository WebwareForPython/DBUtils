

/* wk_isapi.h */

#include "..\common\wkcommon.h"
#include "..\common\marshal.h"
#include "..\common\environ.h"



/*__declspec(dllexport)*/ BOOL WINAPI GetExtensionVersion( HSE_VERSION_INFO* info);

/*__declspec(dllexport)*/ DWORD WINAPI HttpExtensionProc( LPEXTENSION_CONTROL_BLOCK ecb);

