"""Apply WAZEN permissions/signing settings to a freshly generated Flutter iOS project."""
import argparse
from pathlib import Path
import plistlib
import re


def prepare(root: Path, bundle_id: str, team_id: str = ''):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]*(?:\.[A-Za-z0-9-]+)+', bundle_id):
        raise ValueError('A valid reverse-domain bundle identifier is required')
    if team_id and not re.fullmatch(r'[A-Z0-9]{10}', team_id):
        raise ValueError('Apple team ID must contain ten uppercase letters/digits')
    runner = root / 'ios/Runner'
    info_path = runner / 'Info.plist'
    with info_path.open('rb') as source:
        info = plistlib.load(source)
    info.update({
        'CFBundleDisplayName': 'وازن',
        'NSCameraUsageDescription': 'يستخدم وازن الكاميرا لتصوير وجبتك أو مسح باركود الطعام عند طلبك.',
        'NSPhotoLibraryUsageDescription': 'اختر صورة وجبتك لمراجعتها قبل تسجيلها في وازن.',
        'NSMicrophoneUsageDescription': 'يستخدم وازن الميكروفون عندما تختار وصف وجبتك بالصوت.',
        'NSSpeechRecognitionUsageDescription': 'تحويل وصف وجبتك بالصوت إلى نص تراجعه قبل التسجيل.',
    })
    with info_path.open('wb') as target:
        plistlib.dump(info, target, sort_keys=False)
    with (runner / 'Runner.entitlements').open('wb') as target:
        plistlib.dump({'keychain-access-groups': ['$(AppIdentifierPrefix)$(CFBundleIdentifier)']}, target)
    project_path = root / 'ios/Runner.xcodeproj/project.pbxproj'
    project = project_path.read_text()
    def configure(match):
        original = match.group(1).strip('"')
        if original.endswith('.RunnerTests'):
            return f'PRODUCT_BUNDLE_IDENTIFIER = {bundle_id}.RunnerTests;'
        result = f'PRODUCT_BUNDLE_IDENTIFIER = {bundle_id};\n\t\t\t\tCODE_SIGN_ENTITLEMENTS = Runner/Runner.entitlements;'
        if team_id:
            result += f'\n\t\t\t\tDEVELOPMENT_TEAM = {team_id};'
        return result
    # Generated projects are disposable build inputs; start from flutter create.
    project = re.sub(r'PRODUCT_BUNDLE_IDENTIFIER = ([^;]+);', configure, project)
    project = re.sub(r'IPHONEOS_DEPLOYMENT_TARGET = [^;]+;', 'IPHONEOS_DEPLOYMENT_TARGET = 15.5;', project)
    project_path.write_text(project)
    podfile = root / 'ios/Podfile'
    if podfile.exists():
        content = podfile.read_text()
        content = re.sub(r"^#?\s*platform :ios,.*$", "platform :ios, '15.5'", content, flags=re.MULTILINE)
        podfile.write_text(content)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('mobile'))
    parser.add_argument('--bundle-id', default='ae.wazen.app')
    parser.add_argument('--team-id', default='')
    args = parser.parse_args()
    prepare(args.root, args.bundle_id, args.team_id)
