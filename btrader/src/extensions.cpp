#include <map>
#include <deque>
#include <limits>
#include <math.h>
#include <string>
#include <vector>
#include <boost/python.hpp>
#include <boost/accumulators/accumulators.hpp>
#include <boost/accumulators/statistics/mean.hpp>
#include <boost/accumulators/statistics/stats.hpp>
#include <boost/accumulators/statistics/variance.hpp>
using namespace boost::python;

// #define DEBUG_AGE
// #define DEBUG_DEAL

#ifdef DEBUG_DEAL
#include <iostream>
#endif

#ifdef DEBUG_AGE
#include <iostream>
#endif

/*
 *  Converting Python iterables to C++ vectors
 */
// PyList<T> --> 1D vector <T>
template <typename T>
inline std::vector<T> to_1d_vector(const boost::python::object &iterable)
{
  return std::vector<T>(
      boost::python::stl_input_iterator<T>(iterable),
      boost::python::stl_input_iterator<T>());
}

// PyList<PyList<T>> --> 2D vector <T>
template <typename T>
inline std::vector<std::vector<T>> to_2d_vector(const boost::python::object &iterable)
{
  std::vector<boost::python::object> intermediate = to_1d_vector<boost::python::object>(iterable);
  std::vector<std::vector<T>> ending;
  for (unsigned short i = 0; i < intermediate.size(); i++)
  {
    ending.push_back(to_1d_vector<T>(*intermediate[i]));
  }
  return ending;
}

// 1D vector <T> --> PyList<T>
template <class T>
inline boost::python::list to_py_list(std::vector<T> vector)
{
  typename std::vector<T>::iterator iter;
  boost::python::list list;
  for (iter = vector.begin(); iter != vector.end(); ++iter)
  {
    list.append(*iter);
  }
  return list;
}

// 1D vector <std::string> --> 1D vector <double>
std::vector<double> strToDouble1DVector(std::vector<std::string> strVec)
{
  std::vector<double> doubleVec(strVec.size());
  std::transform(strVec.begin(), strVec.end(), doubleVec.begin(), [](const std::string &val) {
    return std::stod(val);
  });
  return doubleVec;
}

// 2D vector <std::string> --> 2D vector <double>
std::vector<std::vector<double>> strToDouble2DVector(std::vector<std::vector<std::string>> strVec)
{
  std::vector<std::vector<double>> doubleVec(strVec.size());
  std::transform(strVec.begin(), strVec.end(), doubleVec.begin(), [](const std::vector<std::string> &val) {
    return strToDouble1DVector(val);
  });
  return doubleVec;
}

/*
 *  General purpose helper functions
 */
double correctQuantity(double quantity, double step)
{
  return (floor(quantity / step) * step);
}

/*
 *  Trading actions and quantities
 */
struct Action
{
public:
  Action(std::string pair, std::string action, double quantity)
  {
    this->pair = pair;
    this->action = action;
    this->quantity = quantity;
  }

  std::string getPair()
  {
    return this->pair;
  }

  std::string getAction()
  {
    return this->action;
  }

  double getQuantity()
  {
    return this->quantity;
  }

private:
  std::string pair;
  std::string action;
  double quantity;
};

/*
 *  Full set of trading actions
 */
struct Deal
{
public:
  void addAction(std::string pair, std::string action, double quantity)
  {
    this->actions.push_back(Action(pair, action, quantity));
  }
  boost::python::list getActions()
  {
    return to_py_list<Action>(actions);
  }
  void setProfit(double profit)
  {
    this->profit = profit;
  }
  double getProfit()
  {
    return this->profit;
  }
  void setTimestamp(double timestamp)
  {
    this->timestamp = timestamp;
  }
  double getTimestamp()
  {
    return this->timestamp;
  }

private:
  double profit = -1;
  double timestamp = 0;
  std::vector<Action> actions;
};

/*
 *  Trading pair wrapper
 */
struct Pair
{
public:
  Pair(std::string name, double step)
  {
    this->symbol = name;
    this->step = step;
    this->timestamp = 0;
  };

  void update(double timestamp, std::vector<std::vector<std::string>> asks, std::vector<std::vector<std::string>> bids)
  {
    std::vector<std::vector<double>> asksDouble = strToDouble2DVector(asks);
    std::vector<std::vector<double>> bidsDouble = strToDouble2DVector(bids);
    this->initialized = true;
    this->timestamp = timestamp;
    this->asks = asksDouble;
    this->bids = bidsDouble;
  }

  double getStep()
  {
    return this->step;
  }

  double getTimestamp()
  {
    return this->timestamp;
  }

  std::vector<std::vector<double>> getAsks()
  {
    return this->asks;
  }

  std::vector<std::vector<double>> getBids()
  {
    return this->bids;
  }

  bool isInitialized()
  {
    return this->initialized;
  }

private:
  bool initialized = false;
  std::string symbol;
  double step;
  double timestamp;
  std::vector<std::vector<double>> asks;
  std::vector<std::vector<double>> bids;
};

/*
 *  Triangular relationship wrapper
 */
struct Relationship
{
public:
  Relationship(std::vector<std::string> pairs, std::vector<std::string> actions)
  {
    this->pairs = pairs;
    this->actions = actions;
  }

  std::vector<std::string> getPairs()
  {
    return this->pairs;
  }

  std::vector<std::string> getActions()
  {
    return this->actions;
  }

  void setInitialized()
  {
    this->initialized = true;
  }

  bool isInitialized()
  {
    return this->initialized;
  }

private:
  bool initialized = false;
  std::vector<std::string> pairs;
  std::vector<std::string> actions;
};

/*
 *  Main class
 */
struct TraderMatrix
{
public:
  TraderMatrix(double fee, boost::python::object quantityRange)
  {
    this->fee = fee;
    this->feeMultiplier = pow((100 - fee) / 100, 3);
    this->qtyRange = to_1d_vector<double>(quantityRange);
  }

  void createPair(std::string symbol, double step)
  {
    this->pairs.insert(std::make_pair(symbol, new Pair(symbol, step)));
    this->pairsLen++;
  }

  void createRelationship(std::string relationshipName, boost::python::list pairs, boost::python::list actions)
  {
    std::vector<std::string> vecPairs = to_1d_vector<std::string>(pairs);
    std::vector<std::string> vecActions = to_1d_vector<std::string>(actions);
    this->relationships.insert(std::make_pair(relationshipName, new Relationship(vecPairs, vecActions)));
  }

  void updatePair(std::string symbol, double timestamp, boost::python::list asks, boost::python::list bids)
  {
    std::vector<std::vector<std::string>> vecAsks = to_2d_vector<std::string>(asks);
    std::vector<std::vector<std::string>> vecBids = to_2d_vector<std::string>(bids);
    this->pairs[symbol]->update(timestamp, vecAsks, vecBids);
  }

  Deal computeRelationship(std::string relationshipName)
  {

    double bestProfit = -1;
    Relationship *rel = this->relationships[relationshipName];
    std::vector<std::string> pairNames = rel->getPairs();
    std::vector<std::string> pairActions = rel->getActions();
    double lowestTimestamp = std::numeric_limits<double>::max();
    double timestamp = 0;
    double profit = 0;          // This will be used to hold iteration profit
    double currentQuantity = 0; // This will be used to compute quantities across currencies
    double helperQuantity = 0;  // This will be used to check for quantities across prices
    double tmpQuantity = 0;
    Deal results = Deal(); // This will hold values before they are converted to PyList
    Deal tmpDeal;

    if (!rel->isInitialized())
    {
      bool initialize = true;
      for (unsigned short i = 0; i < pairNames.size(); i++)
        if (!this->pairs[pairNames[i]]->isInitialized())
          initialize = false;
      if (initialize)
        rel->setInitialized();
      else
      {
        return results;
      }
    }

    for (unsigned short i = 0; i < this->qtyRange.size(); i++)
    {
      // Getting initial quantity
      currentQuantity = this->qtyRange[i];
#ifdef DEBUG_DEAL
      std::cout << "------------------------------" << std::endl;
      std::cout << "Initial: " << currentQuantity << "BTC" << std::endl;
#endif
      tmpDeal = Deal();
      for (unsigned short j = 0; j < pairNames.size(); j++)
      {
        timestamp = this->pairs[pairNames[j]]->getTimestamp();
        if (timestamp < lowestTimestamp)
          lowestTimestamp = timestamp;
        helperQuantity = currentQuantity;
        currentQuantity = 0;
        if (pairActions[j].compare("BUY") == 0)
        {
          // Buying means diving by the price
          // When you're buying, your balance depends on the step size
          std::vector<std::vector<double>> prices = this->pairs[pairNames[j]]->getAsks();
          for (unsigned short k = 0; k < prices.size(); k++)
          {
#ifdef DEBUG_DEAL
            std::cout << pairNames[j] << " Order book: Price=" << prices[k][0] << " TotalQty=" << prices[k][1] << std::endl;
#endif
            // Each item on prices is a vector of two elements
            // Index 0 refers to the price
            // Index 1 refers to the quantity on that price
            tmpQuantity = correctQuantity(helperQuantity / prices[k][0], this->pairs[pairNames[j]]->getStep());
#ifdef DEBUG_DEAL
            std::cout << "HelperQty=" << helperQuantity << " TmpQty=" << tmpQuantity << std::endl;
#endif
            if (prices[k][1] >= tmpQuantity)
            {
              tmpQuantity = correctQuantity(helperQuantity / prices[k][0], this->pairs[pairNames[j]]->getStep());
              currentQuantity += tmpQuantity;
#ifdef DEBUG_DEAL
              std::cout << "Buying quota" << std::endl;
              std::cout << "Trade #" << j + 1 << ": " << pairActions[j] << " " << helperQuantity << " for " << currentQuantity << " " << pairNames[j] << "(price: " << prices[k][0] << ")" << std::endl;
              std::cout << "--" << std::endl;
#endif
            }
            else
            {
              tmpQuantity = correctQuantity(prices[k][1], this->pairs[pairNames[j]]->getStep());
              currentQuantity += tmpQuantity;
#ifdef DEBUG_DEAL
              std::cout << "Buying whole thing" << std::endl;
              std::cout << "Trade #" << j + 1 << ": " << pairActions[j] << " " << (prices[k][1] * prices[k][0]) << " for " << currentQuantity << " " << pairNames[j] << "(price: " << prices[k][0] << ")" << std::endl;
              std::cout << "--" << std::endl;
#endif
            }
            helperQuantity -= (prices[k][1] * prices[k][0]);
            if (helperQuantity <= 0)
              break;
          }
          tmpDeal.addAction(pairNames[j], pairActions[j], currentQuantity);
        }
        else
        {
          // Selling means multiplying by the price
          tmpDeal.addAction(pairNames[j], pairActions[j], correctQuantity(helperQuantity, this->pairs[pairNames[j]]->getStep()));
          std::vector<std::vector<double>> prices = this->pairs[pairNames[j]]->getBids();
          for (unsigned short k = 0; k < prices.size(); k++)
          {
#ifdef DEBUG_DEAL
            std::cout << pairNames[j] << " Order book: Price=" << prices[k][0] << " TotalQty=" << prices[k][1] << std::endl;
#endif
            // Each item on prices is a vector of two elements
            // Index 0 refers to the price
            // Index 1 refers to the quantity on that price
            if (prices[k][1] >= helperQuantity)
            {
              currentQuantity += correctQuantity(helperQuantity, this->pairs[pairNames[j]]->getStep()) * prices[k][0];
#ifdef DEBUG_DEAL
              std::cout << "Selling quota" << std::endl;
              std::cout << "Trade #" << j + 1 << ": " << pairActions[j] << " " << correctQuantity(helperQuantity, this->pairs[pairNames[j]]->getStep()) << " for " << currentQuantity << " " << pairNames[j] << "(price: " << prices[k][0] << ")" << std::endl;
              std::cout << "--" << std::endl;
#endif
            }
            else
            {
              currentQuantity += correctQuantity(prices[k][1], this->pairs[pairNames[j]]->getStep()) * prices[k][0];
#ifdef DEBUG_DEAL
              std::cout << "Selling whole thing" << std::endl;
              std::cout << "Trade #" << j + 1 << ": " << pairActions[j] << " " << correctQuantity(prices[k][1], this->pairs[pairNames[j]]->getStep()) << " for " << currentQuantity << " " << pairNames[j] << "(price: " << prices[k][0] << ")" << std::endl;
              std::cout << "--" << std::endl;
#endif
            }
            helperQuantity -= prices[k][1];
            if (helperQuantity <= 0)
              break;
          }
        }
      }
      // Computing profits
      // profit = ((Current Quantity * Fee Deductions) - Start Quantity) / Start Quantity
      profit = ((currentQuantity * feeMultiplier) - this->qtyRange[i]) / this->qtyRange[i];
      if (profit >= bestProfit)
      {
        results = tmpDeal;
        bestProfit = profit;
      }
#ifdef DEBUG_DEAL
      std::cout << "Profit: " << profit << std::endl;
#endif
    }

    results.setProfit(bestProfit);
    results.setTimestamp(lowestTimestamp);

    return results;
  }

  void addAge(double age)
  {
    if (age > 1e10)
      return;
    if (this->ageDeque.size() >= this->pairsLen)
      this->ageDeque.pop_front();
    this->ageDeque.push_back(age);
  }

  boost::python::list getAverageAge()
  {
    double val;
    double bestAge = std::numeric_limits<double>::max();
    std::vector<double> results;
    boost::accumulators::accumulator_set<double, boost::accumulators::stats<boost::accumulators::tag::mean, boost::accumulators::tag::variance>> acc;
    for (unsigned int i = 0; i < this->ageDeque.size(); i++)
    {
      val = this->ageDeque.at(i);
      acc(val);
      if (val < bestAge)
        bestAge = val;
    }

#ifdef DEBUG_AGE
    std::cout << "Size: " << this->ageDeque.size() << " / Count: " << boost::accumulators::count(acc) << " / Mean: " << boost::accumulators::mean(acc) << " / Std: " << sqrt(boost::accumulators::variance(acc)) << std::endl;
#endif

    results.push_back(boost::accumulators::mean(acc));
    results.push_back(sqrt(boost::accumulators::variance(acc)));
    results.push_back(bestAge);

    return to_py_list<double>(results);
  }

private:
  double fee;
  double pairsLen = 0;
  double feeMultiplier;
  std::deque<double> ageDeque;
  std::vector<double> qtyRange;
  std::map<std::string, Pair *> pairs;
  std::map<std::string, Relationship *> relationships;
};

BOOST_PYTHON_MODULE(extensions)
{
  class_<Deal>("Deal", init<>())
      .def("getProfit", &Deal::getProfit)
      .def("getActions", &Deal::getActions)
      .def("getTimestamp", &Deal::getTimestamp);
  class_<TraderMatrix>("TraderMatrix", init<double, boost::python::object>())
      .def("createPair", &TraderMatrix::createPair)
      .def("createRelationship", &TraderMatrix::createRelationship)
      .def("updatePair", &TraderMatrix::updatePair)
      .def("computeRelationship", &TraderMatrix::computeRelationship)
      .def("addAge", &TraderMatrix::addAge)
      .def("getAverageAge", &TraderMatrix::getAverageAge);
  class_<Action>("Action", init<std::string, std::string, double>())
      .def("getPair", &Action::getPair)
      .def("getAction", &Action::getAction)
      .def("getQuantity", &Action::getQuantity);
}
