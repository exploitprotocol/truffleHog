import argparse
import json
import pprint
import shutil
from urllib.parse import quote_plus, urlparse

import time
from github import Github

from truffleHog import find_strings, del_rw
from slackNotifications import send2slack


def remove_diff(d):
    if not isinstance(d, (dict, list)):
        return d
    if isinstance(d, list):
        return [remove_diff(v) for v in d]
    return {k: remove_diff(v) for k, v in d.items()
            if k not in {'diff', 'printDiff'}}


def main():
    parser = argparse.ArgumentParser(description='Find secrets hidden in the depths of git orgs.')

    parser.add_argument("--org", type=str, dest="orgname", help="Name of organization")
    parser.add_argument("--username", type=str, dest="priv_username", help="Name of user the privtoken belongs to")

    parser.add_argument("--repo", type=str, dest="repo", help="Name of specific repository")

    parser.add_argument("--privtoken", type=str, dest="privtoken", help="Github Token to access private organization")
    parser.add_argument("--pubtoken", type=str, dest="pubtoken",
                        help="Used with --pubrepos, token of account which doesn't have access to the private org")

    parser.add_argument('--notifySlackurl', type=str, dest="slackUrl",
                        help='send the results to slack using the following webhook')

    parser.add_argument('--notifySlackChannel', type=str, dest="slackChannel",
                        help='send the results to slack to the target channel, to be used in conjuction '
                             'with --notifySlackurl')

    parser.add_argument('-v', help="verbosity, if enabled it will print the git diffs of the findings", dest="verbose",
                        action='store_true')
    parser.add_argument('--pubrepos', dest="pubrepos",
                        help='enable searching for repos in the private org which also exist on public github',
                        action="store_true")
    parser.add_argument('--notifySlackCompletion',
                        help="post on slack when execution complete, if enabled it will print a message on slack instead of the full results",
                        dest="notify_slack",
                        action='store_true')
    parser.add_argument('--delay',
                        help="in case of big orgs, sleep <delay> seconds between repos",
                        dest="delay",
                        type=int)

    parser.set_defaults(repo=None)
    parser.set_defaults(delay=0)
    parser.set_defaults(orgname=None)
    parser.set_defaults(privtoken=None)
    parser.set_defaults(pubtoken=None)
    parser.set_defaults(slackUrl=None)
    parser.set_defaults(slackChannel=None)

    args = parser.parse_args()
    output = get_org_repos(orgname=args.orgname, public_token=args.pubtoken, private_token=args.privtoken,
                           repo=args.repo, delay=args.delay)
    if args.verbose is False:
        output = remove_diff(json.loads(json.dumps(output, indent=4, sort_keys=True)))

    if args.slackUrl is not None:
        if args.notify_slack is True:
            send2slack(webhook_url=args.slackUrl, channel=args.slackChannel,
                       msg="Trufflehog execution complete")
        else:
            send2slack(webhook_url=args.slackUrl, channel=args.slackChannel,
                       msg=json.dumps(output, indent=4, sort_keys=True))

    print(json.dumps(output, indent=4, sort_keys=True))


def get_org_repos(orgname='', public_token=None, private_token=None, repo=None, delay=0):
    public = Github(login_or_token=public_token)
    private = Github(login_or_token=private_token)
    output = dict()
    repos = list()

    if repo is not None:
        all_repos = list()
        all_repos.append(private.get_organization(orgname).get_repo(repo))
    else:
        all_repos = private.get_organization(orgname).get_repos(type='all')
    print(orgname + " has " + str(
        private.get_organization(orgname).total_private_repos) + " repos, this might take a while")

    for repo in all_repos:
        repos.append(repo)
        repo_url = urlparse(repo.html_url)

        url = repo_url.scheme + "://" + private_token + ":x-oauth-basic@" + repo_url.netloc + repo_url.path
        print("Checking " + repo_url.path)
        # max_depth is a hack! trufflehog uses gitPython to iterate commits, gitPython iterates 0 commits when it's max depth is 0 and there's no other way to ask "gimme all commits ever"
        # TODO: fix
        strings = find_strings(url, print_json=True, do_entropy=True, do_regex=True, max_depth=999999999999999999999999)
        output.update({repo.html_url: (strings["entropicDiffs"], strings["found_regexes"])})
        project_path = strings["project_path"]
        shutil.rmtree(project_path, onerror=del_rw)
        if delay > 0:
            time.sleep(delay)
    return output


if __name__ == "__main__":
    main()
