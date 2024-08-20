#
# When branching for an OS release, update and uncomment these lines:
#
# OS := fedora
# OS_VERSION := 41
#
######################################################################

ifeq ($(OS),fedora)
ifeq ($(OS_VERSION),)
OS_VERSION := 41
endif
else ifeq ($(OS),centos-stream)
ifeq ($(OS_VERSION),)
OS_VERSION := 10
endif
else ifeq ($(OS),rhel)
ifeq ($(OS_VERSION),)
OS_VERSION := 10
endif
ifeq ($(COMPOSE_URL),)
$(error COMPOSE_URL must be set for OS=rhel)
endif
export COMPOSE_URL
else
$(error OS must be set to fedora, centos-stream, or rhel)
endif

REQUESTS_CA_BUNDLE := /etc/pki/tls/certs/ca-bundle.crt

export OS OS_VERSION REQUESTS_CA_BUNDLE

PACKAGE_LISTS =					\
	out/freedesktop-Platform.packages	\
	out/freedesktop-Sdk.packages

PROFILE_FILES =					\
	out/runtime-base.profile	\
	out/sdk-base.profile

REPORTS = 					\
	reports/runtime.html 	\
	container.new.yaml 		\
	container-sdk.new.yaml

ifeq ($(OS), fedora)
PACKAGE_LISTS +=				\
	out/gnome-Platform.packages	\
	out/gnome-Sdk.packages

PROFILE_FILES +=                \
	out/runtime.profile			\
	out/sdk.profile

REPORTS += 								\
	reports/applications.json 			\
	reports/application-packages.json
endif

FILE_LISTS = $(patsubst %.packages,%.files,$(PACKAGE_LISTS))

all:
	@echo "Targets:"
	@echo "  report: Generates HTML reports in reports/, and a candidate container.new.yaml"
	@echo "  update: Generates the above files, then copies container.new.yaml to container.yaml"

report: $(REPORTS)

update: report
	cp container.new.yaml container.yaml
	cp container-sdk.new.yaml container-sdk.yaml

reports/runtime.html $(PROFILE_FILES): $(PACKAGE_LISTS) package-notes.txt tools/generate-runtime-report.py tools/util.py runtime-template.html
	./tools/generate-runtime-report.py

$(FILE_LISTS): tools/generate-files.sh tools/list-files.py
	./tools/generate-files.sh $@

$(PACKAGE_LISTS): tools/resolve-files.py $(FILE_LISTS)
	for f in $(patsubst %.packages,%.files,$(PACKAGE_LISTS)) ; do	\
		./tools/resolve-files.py $$f || exit 1;		\
	done

out/fedora-appstream.xml.gz: tools/download-fedora-appstream.sh
	./tools/download-fedora-appstream.sh

out/flathub-appstream.xml.gz: tools/download-flathub-appstream.sh
	./tools/download-flathub-appstream.sh

out/ratings.json: tools/download-reviews.sh
	./tools/download-reviews.sh

reports/applications.json reports/application-packages.json: out/runtime.profile tools/generate-app-reports.py out/fedora-appstream.xml.gz out/flathub-appstream.xml.gz out/ratings.json
	./tools/generate-app-reports.py

container.new.yaml container-sdk.new.yaml: $(PROFILE_FILES) container.in.yaml container-sdk.in.yaml tools/generate-container-yaml.py tools/util.py
	./tools/generate-container-yaml.py

clean:
	rm -f out/* report.html flatpak-runtime.new.yaml

.PHONY: all clean report update
