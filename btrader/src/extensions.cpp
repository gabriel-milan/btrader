#include <map>
#include <limits>
#include <math.h>
#include <string>
#include <vector>
#include <boost/python.hpp>
using namespace boost::python;

// #include <iostream>

/*
 *  TODO:
 *  - Implement asset precisions flooring
 */

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

  boost::python::list computeRelationship(std::string relationshipName)
  {

    double bestQty = -1;
    double bestProfit = -1;
    Relationship *rel = this->relationships[relationshipName];
    std::vector<std::string> pairNames = rel->getPairs();
    std::vector<std::string> pairActions = rel->getActions();
    double lowestTimestamp = std::numeric_limits<double>::max();
    double timestamp = 0;
    double profit = 0;           // This will be used to hold iteration profit
    double currentQuantity = 0;  // This will be used to compute quantities across currencies
    double helperQuantity = 0;   // This will be used to check for quantities across prices
    std::vector<double> results; // This will hold values before they are converted to PyList

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
        results.push_back(-1);
        results.push_back(-1);
        results.push_back(-1);
        return to_py_list<double>(results);
      }
    }

    for (unsigned short i = 0; i < this->qtyRange.size(); i++)
    {
      // Getting initial quantity
      currentQuantity = this->qtyRange[i];
      // std::cout << "------------------------------" << std::endl;
      // std::cout << "Initial: " << currentQuantity << "BTC" << std::endl;
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
            // Each item on prices is a vector of two elements
            // Index 0 refers to the price
            // Index 1 refers to the quantity on that price
            if (prices[k][1] >= helperQuantity)
            {
              currentQuantity += correctQuantity(helperQuantity / prices[k][0], this->pairs[pairNames[j]]->getStep());
              // std::cout << "Trade #" << j + 1 << ": " << pairActions[j] << " " << helperQuantity << " for " << currentQuantity << " " << pairNames[j] << std::endl;
            }
            else
            {
              currentQuantity += correctQuantity(prices[k][1] / prices[k][0], this->pairs[pairNames[j]]->getStep());
              // std::cout << "Trade #" << j + 1 << ": " << pairActions[j] << " " << prices[k][1] << " for " << currentQuantity << " " << pairNames[j] << std::endl;
            }
            helperQuantity -= prices[k][1];
            if (helperQuantity <= 0)
              break;
          }
        }
        else
        {
          // Selling means multiplying by the price
          std::vector<std::vector<double>> prices = this->pairs[pairNames[j]]->getBids();
          for (unsigned short k = 0; k < prices.size(); k++)
          {
            // Each item on prices is a vector of two elements
            // Index 0 refers to the price
            // Index 1 refers to the quantity on that price
            if (prices[k][1] >= helperQuantity)
            {
              currentQuantity += correctQuantity(helperQuantity, this->pairs[pairNames[j]]->getStep()) * prices[k][0];
              // std::cout << "Trade #" << j + 1 << ": " << pairActions[j] << " " << correctQuantity(helperQuantity, this->pairs[pairNames[j]]->getStep()) << " for " << currentQuantity << " " << pairNames[j] << std::endl;
            }
            else
            {
              currentQuantity += correctQuantity(prices[k][1], this->pairs[pairNames[j]]->getStep()) * prices[k][0];
              // std::cout << "Trade #" << j + 1 << ": " << pairActions[j] << " " << correctQuantity(prices[k][1], this->pairs[pairNames[j]]->getStep()) << " for " << currentQuantity << " " << pairNames[j] << std::endl;
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
        bestQty = this->qtyRange[i];
        bestProfit = profit;
      }
      // std::cout << "Profit: " << profit << std::endl;
    }

    results.push_back(bestQty);
    results.push_back(bestProfit);
    results.push_back(lowestTimestamp);

    // Converting to PyList and returning
    return to_py_list<double>(results);
  }

private:
  double fee;
  double feeMultiplier;
  std::vector<double> qtyRange;
  std::map<std::string, Pair *> pairs;
  std::map<std::string, Relationship *> relationships;
};

BOOST_PYTHON_MODULE(extensions)
{
  class_<TraderMatrix>("TraderMatrix", init<double, boost::python::object>())
      .def("createPair", &TraderMatrix::createPair)
      .def("createRelationship", &TraderMatrix::createRelationship)
      .def("updatePair", &TraderMatrix::updatePair)
      .def("computeRelationship", &TraderMatrix::computeRelationship);
}
