// Copyright 2019 Global Phasing Ltd.

#include "gemmi/elem.hpp"   // for Element, find_element
#include "gemmi/fprim.hpp"  // for cromer_libermann_for_array
#include <cstdlib>          // for atof
#include <stdio.h>

#define GEMMI_PROG fprim
#include "options.h"

enum OptionIndex { Energy=4, Wavelen };

static const option::Descriptor Usage[] = {
  { NoOp, 0, "", "", Arg::None,
    "Usage:\n " EXE_NAME " [options] ELEMENT[...]"
    "\nPrints anomalous scattering factors f' and f\"."},
  CommonUsage[Help],
  CommonUsage[Version],
  //CommonUsage[Verbose],
  { Energy, 0, "e", "energy", Arg::Float,
    "  -e, --energy=ENERGY  \tEnergy [eV]" },
  { Wavelen, 0, "w", "wavelength", Arg::Float,
    "  -w, --wavelength=LAMBDA  \tWavelength [A]" },
  { 0, 0, 0, 0, 0, 0 }
};

int GEMMI_MAIN(int argc, char **argv) {
  const double hc = 12398.4197386209; // $ units -d15 'h * c / eV / angstrom'
  OptParser p(EXE_NAME);
  p.simple_parse(argc, argv, Usage);
  if (!p.options[Energy] && !p.options[Wavelen]) {
    fprintf(stderr, "Neither energy nor wavelength was specified.\n");
    return -1;
  }
  for (int i = 0; i < p.nonOptionsCount(); ++i) {
    const char* name = p.nonOption(i);
    gemmi::Element elem = gemmi::find_element(name);
    if (elem == gemmi::El::X) {
      fprintf(stderr, "Error: element name not recognized: '%s'\n", name);
      return -1;
    }
    std::vector<double> energies;
    for (const option::Option* opt = p.options[Energy]; opt; opt = opt->next())
      energies.push_back(atof(opt->arg));
    for (const option::Option* opt = p.options[Wavelen]; opt; opt = opt->next())
      energies.push_back(hc / atof(opt->arg));
    std::vector<double> fp(energies.size(), 0);
    std::vector<double> fpp(energies.size(), 0);
    printf("Element\tE[eV]\tWavelength[A]\tf'\tf\"\n");
    gemmi::cromer_libermann_for_array(elem.atomic_number(),
                                      (int) energies.size(), energies.data(),
                                      &fp[0], &fpp[0]);
    for (size_t j = 0; j != energies.size(); ++j) {
      printf("%s\t%g\t%-9g\t%.5g\t%.5g\n",
             elem.name(), energies[j], hc / energies[j], fp[j], fpp[j]);
    }
  }
  return 0;
}

// vim:sw=2:ts=2:et:path^=../include,../third_party
